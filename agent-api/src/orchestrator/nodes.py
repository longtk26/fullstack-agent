"""The eight workflow nodes (FR-09). Each is `async (state, ctx) -> (state update, step summary)`."""

import json
import uuid
from pathlib import Path
from typing import Any

from src.configs import config
from src.libs.redaction import default_redactor
from src.modules.shared.domain.backend_spec import validate_spec_text
from src.modules.shared.domain.entities import ValidationRunEntity

from .checks.parity import compare_schema
from .context import EngineFailure, JobContext
from .migrations import ensure_migration, reflect_schema, verify_migration
from .packaging import (
    ArtifactWriter,
    build_logs_zip,
    build_manifest,
    build_report,
    build_seed,
    build_source_zip,
    report_markdown,
)
from .planner import build_plan, dump_plan
from .scaffold import SCAFFOLD_INFO, record_owned, scaffold_project
from .state import GenerationState, Outcome
from .validation import ValidationRequest, write_report

DIGEST_LIMIT = 30_000
PROMPT_VERSION = "v2"
# kind → name of the artifacts the manifest and the generation detail point at
MAIN_ARTIFACTS = {
    "source": "backend.zip",
    "openapi": "openapi.json",
    "manifest": "manifest.json",
    "report": "report.json",
}
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
    plan = build_plan(_read_json(ctx, state["spec_ref"]))
    path = ctx.project_path(".bga", "plan.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_plan(plan))
    summary = {
        "modules": len(plan["modules"]),
        "models": len(plan["models"]),
        "operations": sum(len(m["operations"]) for m in plan["modules"]),
        "tests": len(plan["tests"]),
        "unresolved": len(plan["unresolved"]),
    }
    await ctx.emit("plan.ready", step="plan_architecture", **summary)
    return {"plan_ref": ".bga/plan.json"}, summary


async def _scaffold(state: GenerationState, ctx: JobContext, project_name: str) -> None:
    """Template + overlay, formatted once, owned files recorded, committed as `node:scaffold` (Story 5.2)."""
    project = ctx.workspace.project
    if (project / SCAFFOLD_INFO).exists():
        return
    info = scaffold_project(
        ctx.template_dir, project, project_name, bool(state["options"].get("generateDockerfile", True))
    )
    sandbox = await ctx.sandbox()
    if sandbox is not None:
        # The pinned template is not ruff-clean (import order, unused names); normalize it once.
        await sandbox.exec("ruff check --fix -q . ; ruff format -q .", timeout_s=120)
    record_owned(project)
    ctx.workspaces.commit(ctx.workspace, "node:scaffold")
    await ctx.emit("scaffold.done", step="generate_database", **info)


async def _schema_post_check(ctx: JobContext, plan: dict[str, Any]) -> dict[str, Any]:
    """Story 5.3: autogenerate the migration in the sandbox and compare the migrated schema with the plan.
    Problems are reported here and enforced by run_validation (where repair can fix them)."""
    sandbox = await ctx.sandbox()
    if sandbox is None:
        return {"migration": "not_run"}
    generated, _ = await ensure_migration(sandbox, ctx.workspace.project)
    if generated is not None and not generated.ok:
        result = {"migration": "autogenerate_failed"}
    else:
        verify = await verify_migration(sandbox)
        schema, _ = await reflect_schema(sandbox) if verify.ok else (None, None)
        problems = compare_schema(plan, schema) if schema is not None else None
        result = {
            "migration": "ok" if verify.ok else "failed",
            "schemaProblems": len(problems) if problems is not None else None,
        }
        if problems:
            result["firstProblems"] = [f"{p['table']}: {p['message']}" for p in problems[:5]]
    await ctx.emit("schema.check", step="generate_database", **result)
    return result


async def generate_database(state: GenerationState, ctx: JobContext) -> NodeResult:
    spec = _read_json(ctx, state["spec_ref"])
    plan = _read_json(ctx, state["plan_ref"])
    await _scaffold(state, ctx, spec["project"]["name"])
    prompt = ctx.prompts.render(
        "generate_database",
        PROMPT_VERSION,
        project_name=spec["project"]["name"],
        spec_path=state["spec_ref"],
        plan_path=state["plan_ref"],
        models=plan["models"],
        file_tree=ctx.file_tree(),
    )
    result = await ctx.run_engine("generate_database", "generate_database", prompt)
    return {}, {"changedFiles": len(result.changed_files), **await _schema_post_check(ctx, plan)}


async def generate_backend(state: GenerationState, ctx: JobContext) -> NodeResult:
    plan = _read_json(ctx, state["plan_ref"])
    changed = 0
    for module in plan["modules"]:
        prompt = ctx.prompts.render(
            "generate_backend",
            PROMPT_VERSION,
            module=module,
            module_json=json.dumps({k: v for k, v in module.items() if k != "tests"}, indent=2, sort_keys=True),
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
            PROMPT_VERSION,
            module=module,
            test_cases=module["tests"],
            spec_path=state["spec_ref"],
            plan_path=state["plan_ref"],
        )
        await ctx.run_engine("generate_tests", "generate_tests", prompt)
    return {}, {"modules": len(plan["modules"])}


async def run_validation(state: GenerationState, ctx: JobContext) -> NodeResult:
    attempt = state.get("repair_attempts", 0) + 1
    request = ValidationRequest(
        project=ctx.workspace.project,
        plan=_read_json(ctx, state["plan_ref"]),
        run_tests=bool(state["options"].get("runTests", True)),
        sandbox=await ctx.sandbox(),
    )
    outcome = await ctx.validator.run(request)
    for name, document in request.artifacts.items():
        _write_json(ctx.workspace.reports / f"{name}.json", document)
    for check in outcome.results:
        ctx.store.add_validation_run(
            ValidationRunEntity(
                generation_id=ctx.generation_id,
                attempt=attempt,
                check=check.check,
                status=check.status,
                duration_ms=check.duration_ms,
                details={"summary": check.summary, "items": check.details[:50], "output": check.output[-4000:]},
            )
        )
        await ctx.emit(
            "validation.check",
            step="run_validation",
            status=check.status,
            check=check.check,
            summary=check.summary,
            durationMs=check.duration_ms,
            attempt=attempt,
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
        PROMPT_VERSION,
        attempt=attempt,
        max_attempts=state["max_repair_attempts"],
        failed_checks=state.get("failed_checks", []),
        implicated_files=state.get("implicated_files", []),
        failure_digest=digest or "(no output captured)",
        plan_path=state["plan_ref"],
    )
    try:
        result = await ctx.run_engine("repair_code", "repair_code", prompt)
    except EngineFailure:
        # An engine hiccup is not a code failure: retry once before giving up (Story 6.3).
        await ctx.emit("engine.retry", step="repair_code", attempt=attempt)
        result = await ctx.run_engine("repair_code", "repair_code", prompt)
    return {"repair_attempts": attempt}, {"attempt": attempt, "changedFiles": result.changed_files[:50]}


def _optional_json(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text()) if path.is_file() else None


async def write_artifacts(ctx: JobContext, state: dict[str, Any], completed: bool, error: str | None = None):
    """Story 7.1 (COMPLETED: everything) and 7.2 (FAILED: report, patches, validation reports, engine logs)."""
    generation = ctx.store.generation(ctx.generation_id)
    workspace, project = ctx.workspace, ctx.workspace.project
    writer = ArtifactWriter(
        Path(config.artifact_root), ctx.generation_id, {a.name: a.id for a in ctx.store.artifacts(ctx.generation_id)}
    )
    spec = _optional_json(project / ".bga" / "spec.json") or {}
    plan = _optional_json(project / ".bga" / "plan.json") or {}

    if (workspace.spec_dir / "spec.raw.json").is_file():
        writer.write("spec.json", "spec", (workspace.spec_dir / "spec.raw.json").read_bytes(), "application/json")
    if plan:
        writer.write_json("plan.json", "plan", plan)
    for name, diff in ctx.workspaces.repair_patches(workspace):
        writer.write(name, "patch", diff.encode(), "text/x-diff")
    for path in sorted(workspace.reports.glob("validation-*.json")):
        writer.write(path.name, "validation", path.read_bytes(), "application/json")

    report = build_report(
        generation=generation,
        outcome="COMPLETED" if completed else "FAILED",
        error=error,
        node_runs=ctx.store.node_runs(ctx.generation_id),
        validation_runs=ctx.store.validation_runs(ctx.generation_id),
        invocations=ctx.store.cli_invocations(ctx.generation_id),
    )
    writer.write_json("report.json", "report", report)
    project_name = (spec.get("project") or {}).get("name")
    writer.write("report.md", "report", report_markdown(report, project_name).encode(), "text/markdown")

    operations = 0
    if completed:
        writer.write("backend.zip", "source", build_source_zip(project), "application/zip")
        openapi = _optional_json(workspace.reports / "openapi.json")
        if openapi:
            writer.write_json("openapi.json", "openapi", openapi)
        if spec.get("seed"):
            timestamp = generation.created_at.isoformat() if generation.created_at else "1970-01-01T00:00:00+00:00"
            writer.write_json("seed.json", "seed", build_seed(spec, plan, ctx.generation_id, timestamp))
        artifact_ids = {
            kind: writer.artifact_id(name)
            for kind, name in MAIN_ARTIFACTS.items()
            if kind != "openapi" or openapi is not None
        }
        manifest = build_manifest(
            generation=generation,
            generator_version=config.generator_version,
            spec=spec,
            plan=plan,
            openapi=openapi,
            scaffold=_optional_json(project / SCAFFOLD_INFO) or {},
            validation=state.get("validation") or {},
            artifact_ids=artifact_ids,
            project=project,
        )
        operations = len(manifest["operations"])
        writer.write_json("manifest.json", "manifest", manifest)
    else:
        logs = build_logs_zip(workspace.state / "logs", default_redactor())
        if logs:
            writer.write("engine-logs.zip", "log", logs, "application/zip")

    ctx.store.replace_artifacts(ctx.generation_id, writer.written)
    for artifact in writer.written:
        await ctx.emit(
            "artifact.created",
            step="package_artifacts",
            artifactId=artifact.id,
            name=artifact.name,
            kind=artifact.kind,
            size=artifact.size,
        )
    main = set(MAIN_ARTIFACTS.values())
    return {artifact.kind: artifact.id for artifact in writer.written if artifact.name in main}, operations


async def package_artifacts(state: GenerationState, ctx: JobContext) -> NodeResult:
    artifact_ids, operations = await write_artifacts(ctx, state, completed=True)
    summary = {"artifacts": sorted(artifact_ids), "operations": operations}
    return {"outcome": Outcome.COMPLETED, "artifact_ids": artifact_ids}, summary


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
