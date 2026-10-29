"""The frontend lane (Epic 13): plan → scaffold → generate → validate ⇄ repair. Same shape as the backend nodes:
`async (state, ctx) -> (state update, step summary)`. Paths in state are relative to the frontend repository
(`<workspace>/frontend`), except `frontend_ref`, the normalized FrontendSpec in the workspace's spec directory."""

import json
from pathlib import Path
from typing import Any

from src.modules.shared.domain.entities import ValidationRunEntity
from src.modules.shared.domain.enums import GenerationMode, LaneStatus

from .autofix import autofix_before_validation
from .context import EngineFailure, JobContext
from .frontend_planner import dump_frontend_plan, plan_frontend
from .frontend_scaffold import scaffold_frontend
from .frontend_validation import FrontendValidationRequest
from .integration import package_lane_preview
from .state import GenerationState, Outcome
from .validation import write_report

DIGEST_LIMIT = 30_000
FRONTEND_PROMPTS = {"generate_frontend_shell": "v1", "generate_frontend_page": "v1", "repair_frontend": "v1"}
PLAN_REF = ".bga/frontend-plan.json"
CHECK_PREFIX = "frontend:"
NodeResult = tuple[dict[str, Any], dict[str, Any]]


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _contract(ctx: JobContext) -> dict[str, Any] | None:
    path = ctx.workspace.spec_dir / "contract.json"
    return _json(path) if path.is_file() else None


def _plan(ctx: JobContext, state: GenerationState) -> dict[str, Any]:
    return _json(ctx.frontend_path(state["frontend_plan_ref"]))


async def plan_frontend_node(state: GenerationState, ctx: JobContext) -> NodeResult:
    spec = _json(Path(state["frontend_ref"]))
    plan = plan_frontend(spec, _contract(ctx))
    ctx.workspaces.create_frontend(ctx.workspace)
    path = ctx.frontend_path(PLAN_REF)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_frontend_plan(plan))
    summary = {
        "routes": len(plan["routes"]),
        "components": len(plan["components"]),
        "shadcn": len(plan["shadcn"]),
        "bindings": len(plan["data"]),
        "forms": len(plan["forms"]),
        "tests": len(plan["tests"]),
    }
    await ctx.emit("frontend.plan.ready", step="plan_frontend", **summary)
    return {"frontend_plan_ref": PLAN_REF}, summary


async def scaffold_frontend_node(state: GenerationState, ctx: JobContext) -> NodeResult:
    """Story 13.2: pinned base + overlay + generated client, mocks, forms, theme and tests."""
    plan = _plan(ctx, state)
    info = scaffold_frontend(ctx.workspace.frontend, plan, _json(Path(state["frontend_ref"])), _contract(ctx))
    summary = {"mode": info["mode"], "shadcn": len(info["shadcn"]), "generated": len(info["generated"])}
    await ctx.emit("frontend.scaffold.done", step="scaffold_frontend", **summary)
    return {}, summary


async def generate_frontend(state: GenerationState, ctx: JobContext) -> NodeResult:
    """Story 13.3: outside-in — the shell and shared components first, then one engine call per page."""
    plan = _plan(ctx, state)
    common = {
        "plan_path": state["frontend_plan_ref"],
        "spec_path": ".bga/frontend-spec.json",
        "mode": plan["project"]["mode"],
    }
    prompt = ctx.prompts.render(
        "generate_frontend_shell",
        FRONTEND_PROMPTS["generate_frontend_shell"],
        shell=plan["shell"],
        components=plan["components"],
        shadcn=plan["shadcn"],
        theme=plan["theme"],
        file_tree=ctx.file_tree(repo="frontend"),
        **common,
    )
    result = await ctx.run_engine("generate_frontend", "generate_frontend", prompt, repo="frontend")
    changed = len(result.changed_files)
    forms = {form["id"]: form for form in plan["forms"]}
    for route in plan["routes"]:
        prompt = ctx.prompts.render(
            "generate_frontend_page",
            FRONTEND_PROMPTS["generate_frontend_page"],
            route=route,
            route_json=json.dumps(route, indent=2, sort_keys=True, ensure_ascii=False),
            data=[binding for binding in plan["data"] if binding["pageId"] == route["pageId"]],
            forms=[forms[s["form"]] for s in route["sections"] if s.get("form") in forms],
            file_tree=ctx.file_tree(repo="frontend"),
            **common,
        )
        result = await ctx.run_engine("generate_frontend", "generate_frontend", prompt, repo="frontend")
        changed += len(result.changed_files)
    return {}, {"pages": len(plan["routes"]), "changedFiles": changed}


async def validate_frontend(state: GenerationState, ctx: JobContext) -> NodeResult:
    attempt = state.get("frontend_repair_attempts", 0) + 1
    canonical_contract = ctx.workspace.spec_dir / "contract.json"
    if canonical_contract.is_file():
        frontend_contract = ctx.frontend_path(".bga", "contract.json")
        frontend_contract.parent.mkdir(parents=True, exist_ok=True)
        frontend_contract.write_text(canonical_contract.read_text())  # undo any edit by the engine
    fixes = await autofix_before_validation(ctx, "frontend", attempt, "validate_frontend")
    plan = _plan(ctx, state)
    frontend_options = state["options"].get("frontend") or {}
    request = FrontendValidationRequest(
        project=ctx.workspace.frontend,
        plan=plan,
        run_tests=bool(frontend_options.get("runTests", True)),
        sandbox=await ctx.frontend_sandbox(),
    )
    outcome = await ctx.frontend_validator.run(request)
    for check in outcome.results:
        ctx.store.add_validation_run(
            ValidationRunEntity(
                generation_id=ctx.generation_id,
                attempt=attempt,
                check=f"{CHECK_PREFIX}{check.check}",
                status=check.status,
                started_at=check.started_at,
                duration_ms=check.duration_ms,
                details={"summary": check.summary, "items": check.details[:50], "output": check.output[-4000:]},
            )
        )
        await ctx.emit(
            "validation.check",
            step="validate_frontend",
            status=check.status,
            check=f"{CHECK_PREFIX}{check.check}",
            summary=check.summary,
            durationMs=check.duration_ms,
            attempt=attempt,
        )
    write_report(ctx.workspace.reports / f"frontend-validation-{attempt}.json", outcome)
    digest_path = ctx.workspace.reports / f"frontend-digest-{attempt}.txt"
    digest_path.write_text(outcome.digest[:DIGEST_LIMIT])

    failed = outcome.failed_checks
    update: dict[str, Any] = {
        "frontend_validation": outcome.summary,
        "frontend_failed_checks": failed,
        "frontend_digest_ref": str(digest_path),
        "frontend_implicated_files": outcome.implicated_files,
    }
    limit = state["max_repair_attempts"]
    if not failed:
        await ctx.set_lane("frontend", LaneStatus.COMPLETED)
        if ctx.mode == GenerationMode.DYNAMIC:
            ctx.start_integration_wait_watchdog()
            await package_lane_preview(state, ctx, "frontend")
    elif state.get("frontend_repair_attempts", 0) >= limit:
        message = (
            f"Frontend validation still failing after {state.get('frontend_repair_attempts', 0)} repair "
            f"attempt(s): {', '.join(failed)}"
        )
        await ctx.set_lane("frontend", LaneStatus.FAILED, reason=message)
        await ctx.abort_backend("frontend lane failed", frontend_failed=True)
        update["outcome"] = Outcome.REPAIR_LIMIT
        update["error_summary"] = message
    return update, {"_status": "failed" if failed else "succeeded", "failedChecks": failed, **fixes}


async def repair_frontend(state: GenerationState, ctx: JobContext) -> NodeResult:
    attempt = state.get("frontend_repair_attempts", 0) + 1
    await ctx.emit(
        "repair.attempt",
        step="repair_frontend",
        attempt=attempt,
        maxAttempts=state["max_repair_attempts"],
        failedChecks=state.get("frontend_failed_checks", []),
    )
    digest_ref = state.get("frontend_digest_ref")
    digest = Path(digest_ref).read_text() if digest_ref else ""
    prompt = ctx.prompts.render(
        "repair_frontend",
        FRONTEND_PROMPTS["repair_frontend"],
        attempt=attempt,
        max_attempts=state["max_repair_attempts"],
        failed_checks=state.get("frontend_failed_checks", []),
        implicated_files=state.get("frontend_implicated_files", []),
        failure_digest=digest or "(no output captured)",
        plan_path=state["frontend_plan_ref"],
    )
    try:
        result = await ctx.run_engine("repair_frontend", "repair_frontend", prompt, repo="frontend")
    except EngineFailure:
        await ctx.emit("engine.retry", step="repair_frontend", attempt=attempt)
        result = await ctx.run_engine("repair_frontend", "repair_frontend", prompt, repo="frontend")
    return {"frontend_repair_attempts": attempt}, {"attempt": attempt, "changedFiles": result.changed_files[:50]}


FRONTEND_NODE_FUNCTIONS = {
    "plan_frontend": plan_frontend_node,
    "scaffold_frontend": scaffold_frontend_node,
    "generate_frontend": generate_frontend,
    "validate_frontend": validate_frontend,
    "repair_frontend": repair_frontend,
}
