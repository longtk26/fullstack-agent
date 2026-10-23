"""The eight workflow nodes (FR-09). Each is `async (state, ctx) -> (state update, step summary)`."""

import json
import uuid
from typing import Any

from src.modules.shared.domain.backend_spec import validate_spec_text
from src.modules.shared.domain.entities import ValidationRunEntity

from .context import EngineFailure, JobContext
from .planning import skeleton_plan
from .state import GenerationState, Outcome
from .validation import write_report

DIGEST_LIMIT = 30_000
NodeResult = tuple[dict[str, Any], dict[str, Any]]


def _read_json(ctx: JobContext, ref: str) -> dict[str, Any]:
    return json.loads(ctx.project_path(ref).read_text())


def _write_json(path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


async def validate_spec(state: GenerationState, ctx: JobContext) -> NodeResult:
    spec = ctx.store.spec(uuid.UUID(state["spec_id"]))
    result = validate_spec_text(spec.raw_json)
    _write_json(ctx.workspace.spec_dir / "validation-report.json", result.report.model_dump(mode="json"))
    (ctx.workspace.spec_dir / "spec.raw.json").write_text(spec.raw_json)
    if not result.report.valid:
        errors = result.report.errors
        await ctx.emit(
            "spec.invalid",
            step="validate_spec",
            errors=[issue.model_dump(mode="json") for issue in errors[:20]],
            total=len(errors),
        )
        summary = f"BackendSpec has {len(errors)} error(s); first: {errors[0].path} {errors[0].message}"
        return {"spec_valid": False, "outcome": Outcome.SPEC_INVALID, "error_summary": summary}, {
            "_status": "failed",
            "errors": len(errors),
        }
    _write_json(ctx.project_path(".bga", "spec.json"), result.normalized)
    return {"spec_valid": True, "spec_ref": ".bga/spec.json"}, {"warnings": len(result.report.warnings)}


async def plan_architecture(state: GenerationState, ctx: JobContext) -> NodeResult:
    plan = skeleton_plan(_read_json(ctx, state["spec_ref"]))
    _write_json(ctx.project_path(".bga", "plan.json"), plan)
    return {"plan_ref": ".bga/plan.json"}, {"modules": len(plan["modules"])}


async def generate_database(state: GenerationState, ctx: JobContext) -> NodeResult:
    spec = _read_json(ctx, state["spec_ref"])
    prompt = ctx.prompts.render(
        "generate_database",
        project_name=spec["project"]["name"],
        spec_path=state["spec_ref"],
        plan_path=state["plan_ref"],
        entities=[entity["name"] for entity in spec.get("entities", [])],
        file_tree=ctx.file_tree(),
    )
    result = await ctx.run_engine("generate_database", "generate_database", prompt)
    return {}, {"changedFiles": len(result.changed_files)}


async def generate_backend(state: GenerationState, ctx: JobContext) -> NodeResult:
    plan = _read_json(ctx, state["plan_ref"])
    changed = 0
    for module in plan["modules"]:
        prompt = ctx.prompts.render(
            "generate_backend",
            module=module,
            spec_path=state["spec_ref"],
            plan_path=state["plan_ref"],
            file_tree=ctx.file_tree(),
        )
        result = await ctx.run_engine("generate_backend", "generate_backend", prompt)
        changed += len(result.changed_files)
    return {}, {"modules": len(plan["modules"]), "changedFiles": changed}


async def generate_tests(state: GenerationState, ctx: JobContext) -> NodeResult:
    if not state["options"].get("runTests", True):
        return {}, {"_status": "skipped", "reason": "runTests=false"}
    plan = _read_json(ctx, state["plan_ref"])
    for module in plan["modules"]:
        prompt = ctx.prompts.render(
            "generate_tests",
            module=module,
            test_cases=module["tests"],
            spec_path=state["spec_ref"],
            plan_path=state["plan_ref"],
        )
        await ctx.run_engine("generate_tests", "generate_tests", prompt)
    return {}, {"modules": len(plan["modules"])}


async def run_validation(state: GenerationState, ctx: JobContext) -> NodeResult:
    attempt = state.get("repair_attempts", 0) + 1
    outcome = await ctx.validator.run(ctx.workspace.project, state["options"].get("runTests", True))
    for check in outcome.results:
        ctx.store.add_validation_run(
            ValidationRunEntity(
                generation_id=ctx.generation_id,
                attempt=attempt,
                check=check.check,
                status=check.status,
                duration_ms=check.duration_ms,
                details={"summary": check.summary, "items": check.details[:50]},
            )
        )
        await ctx.emit(
            "validation.check", step="run_validation", status=check.status, check=check.check, summary=check.summary
        )
    write_report(ctx.workspace.reports / f"validation-{attempt}.json", outcome)
    digest_path = ctx.workspace.reports / f"digest-{attempt}.txt"
    digest_path.write_text(outcome.digest[:DIGEST_LIMIT])

    failed = outcome.failed_checks
    update: dict[str, Any] = {
        "validation": outcome.summary,
        "failed_checks": failed,
        "failure_digest_ref": str(digest_path),
        "implicated_files": outcome.implicated_files,
    }
    if failed and state.get("repair_attempts", 0) >= state["max_repair_attempts"]:
        update["outcome"] = Outcome.REPAIR_LIMIT
        update["error_summary"] = (
            f"Validation still failing after {state.get('repair_attempts', 0)} repair attempt(s): {', '.join(failed)}"
        )
    return update, {"_status": "failed" if failed else "succeeded", "failedChecks": failed}


async def repair_code(state: GenerationState, ctx: JobContext) -> NodeResult:
    attempt = state.get("repair_attempts", 0) + 1
    ctx.store.update_generation(ctx.generation_id, repair_attempts=attempt)
    await ctx.emit(
        "repair.attempt",
        step="repair_code",
        attempt=attempt,
        maxAttempts=state["max_repair_attempts"],
        failedChecks=state.get("failed_checks", []),
    )
    digest_ref = state.get("failure_digest_ref")
    digest = open(digest_ref).read() if digest_ref else ""
    prompt = ctx.prompts.render(
        "repair_code",
        attempt=attempt,
        max_attempts=state["max_repair_attempts"],
        failed_checks=state.get("failed_checks", []),
        implicated_files=state.get("implicated_files", []),
        failure_digest=digest or "(no output captured)",
        tests_editable=False,
    )
    try:
        result = await ctx.run_engine("repair_code", "repair_code", prompt)
    except EngineFailure:
        # An engine hiccup is not a code failure: retry once before giving up (Story 6.3).
        await ctx.emit("engine.retry", step="repair_code", attempt=attempt)
        result = await ctx.run_engine("repair_code", "repair_code", prompt)
    return {"repair_attempts": attempt}, {"attempt": attempt, "changedFiles": result.changed_files[:50]}


async def package_artifacts(state: GenerationState, ctx: JobContext) -> NodeResult:
    # Story 7.1 adds the ZIP, OpenAPI export, manifest and report here.
    return {"outcome": Outcome.COMPLETED, "artifact_ids": {}}, {"note": "artifact packaging arrives with Epic 7"}


NODE_FUNCTIONS = {
    "validate_spec": validate_spec,
    "plan_architecture": plan_architecture,
    "generate_database": generate_database,
    "generate_backend": generate_backend,
    "generate_tests": generate_tests,
    "run_validation": run_validation,
    "repair_code": repair_code,
    "package_artifacts": package_artifacts,
}
