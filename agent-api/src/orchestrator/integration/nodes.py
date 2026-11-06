"""Nodes before the lanes split and after they meet (Epic 12): validate_inputs (FrontendSpec, BackendSpec and the
pair), build_contract (the API contract), and integrate (`integration.py`)."""

import json
import uuid
from pathlib import Path
from typing import Any

from src.configs import config
from src.modules.shared.domain.backend_spec import Severity, SpecIssue
from src.modules.shared.domain.enums import GenerationMode, SpecSource
from src.modules.shared.domain.frontend_spec import autofix_frontend_spec, validate_frontend_spec_data

from ..backend.nodes import check_backend_spec
from ..backend.planner import build_plan
from ..checks.consistency import check_spec_pair
from ..context import CONTRACT_REF, JobContext, contract_copy, read_json, write_json
from ..packaging import (
    ArtifactWriter,
)
from ..state import GenerationState, NodeResult, Outcome
from .contract import build_contract as contract_for
from .contract import dump_contract
from .integrate import integrate


def _issue_dump(issue: SpecIssue, spec: str) -> dict[str, Any]:
    data = issue.model_dump(mode="json", exclude_none=True)
    if "backend_path" in data:
        data["backendPath"] = data.pop("backend_path")
    return {"spec": spec, **data}


def _reconcile(frontend: dict[str, Any], backend: dict[str, Any]):
    """The pair reconcile (drafted specs), then the reconciled FrontendSpec validated again: a reconcile that
    breaks the spec is reported, not generated. Returns (validation result, notes)."""
    from src.orchestrator.checks.consistency import reconcile_spec_pair

    healed, notes = reconcile_spec_pair(frontend, backend)
    return validate_frontend_spec_data(healed), notes


async def validate_inputs(state: GenerationState, ctx: JobContext) -> NodeResult:
    """Static and dynamic modes (Stories 12.1, 12.5): the FrontendSpec, in dynamic mode also the BackendSpec and
    the frontend ↔ contract consistency check, all before any engine time is spent."""
    frontend = ctx.store.frontend_spec(uuid.UUID(state["frontend_spec_id"]))
    spec_dir = ctx.workspace.spec_dir
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "frontend-spec.raw.json").write_text(frontend.raw_json)  # as submitted (the spec artifact)
    fixed_dict, _ = autofix_frontend_spec(json.loads(frontend.raw_json))
    write_json(spec_dir / "frontend-spec.autofixed.json", fixed_dict)
    result = validate_frontend_spec_data(fixed_dict)
    write_json(spec_dir / "frontend-validation-report.json", result.report.model_dump(mode="json"))
    errors = [_issue_dump(issue, "frontend") for issue in result.report.errors]
    warnings = len(result.report.warnings)
    if result.normalized is not None and result.normalized["project"]["mode"] != state["mode"]:
        errors.append(
            {
                "spec": "frontend",
                "code": "MODE_INPUT_MISMATCH",
                "path": "/project/mode",
                "message": f"The FrontendSpec is for a '{result.normalized['project']['mode']}' site, "
                f"the generation is '{state['mode']}'",
            }
        )

    update: dict[str, Any] = {}
    if state["mode"] == GenerationMode.DYNAMIC:
        backend = check_backend_spec(state, ctx)
        errors += [_issue_dump(issue, "backend") for issue in backend.report.errors]
        warnings += len(backend.report.warnings)
        if result.normalized is not None and backend.normalized is not None:
            if frontend is not None and (
                frontend.source == SpecSource.REQUIREMENT or state.get("draft_id") is not None
            ):
                result, notes = _reconcile(result.normalized, backend.normalized)
                errors += [_issue_dump(issue, "frontend") for issue in result.report.errors]
                warnings += len(notes)
                if notes:
                    write_json(spec_dir / "reconcile-notes.json", notes)
                    write_json(spec_dir / "frontend-validation-report.json", result.report.model_dump(mode="json"))
                    await ctx.emit("spec.reconciled", step="validate_inputs", notes=notes[:20], total=len(notes))
        if result.normalized is not None and backend.normalized is not None:
            consistency = check_spec_pair(result.normalized, backend.normalized)
            write_json(spec_dir / "consistency-report.json", [i.model_dump(mode="json") for i in consistency])
            errors += [_issue_dump(issue, "consistency") for issue in consistency if issue.severity != Severity.WARNING]
            warnings += sum(1 for issue in consistency if issue.severity == Severity.WARNING)
        update["spec_ref"] = ".bga/spec.json"

    if errors:
        await ctx.emit("spec.invalid", step="validate_inputs", errors=errors[:20], total=len(errors))
        first = errors[0]
        summary = f"{len(errors)} input error(s); first: {first['spec']} {first['path']} {first['message']}"
        return {"spec_valid": False, "outcome": Outcome.SPEC_INVALID, "error_summary": summary}, {
            "_status": "failed",
            "errors": len(errors),
        }
    write_json(spec_dir / "frontend-spec.json", result.normalized)
    pages = len(result.normalized["pages"])
    await ctx.emit("inputs.valid", step="validate_inputs", pages=pages, warnings=warnings)
    return {**update, "spec_valid": True, "frontend_ref": str(spec_dir / "frontend-spec.json")}, {
        "pages": pages,
        "warnings": warnings,
    }


async def build_contract(state: GenerationState, ctx: JobContext) -> NodeResult:
    """Story 12.3: the API contract, before either lane starts; stored as an artifact and in the workspace."""
    spec = read_json(ctx, state["spec_ref"])
    plan = build_plan(spec)
    text = dump_contract(contract_for(spec, plan))
    contract_copy(ctx).write_text(text)
    project_copy = ctx.project_path(*CONTRACT_REF.split("/"))
    project_copy.parent.mkdir(parents=True, exist_ok=True)
    project_copy.write_text(text)
    writer = ArtifactWriter(
        Path(config.artifact_root), ctx.generation_id, {a.name: a.id for a in ctx.store.artifacts(ctx.generation_id)}
    )
    artifact = writer.write("contract.json", "contract", text.encode(), "application/json")
    ctx.store.replace_artifacts(ctx.generation_id, [artifact])
    operations = sum(len(module["operations"]) for module in plan["modules"])
    summary = {"operations": operations, "sha256": artifact.sha256, "bytes": artifact.size}
    await ctx.emit("contract.ready", step="build_contract", artifactId=artifact.id, **summary)
    return {"contract_ref": CONTRACT_REF}, summary


INTEGRATION_NODE_FUNCTIONS = {
    "validate_inputs": validate_inputs,
    "build_contract": build_contract,
    "integrate": integrate,
}
