"""Dynamic integration lane (Stories 14.2, 14.3): wait for the backend, MOCK_TEST_API switch, health check.

Each lane's preview starts as soon as the lane passes (`package_lane_preview`, Stories 18.8, 18.12), from any
worker, so the user can use either one while the other lane still runs. After both lanes, `integrate`:
1. Restores the canonical `.bga/contract.json` in both workspaces so neither engine could have altered it.
2. Waits up to `INTEGRATION_WAIT_SECONDS` while the backend lane or its preview is still starting; ready once the
   lane is `COMPLETED` and the preview `RUNNING` (validation already proved the app starts and its API answers).
3. If ready, restarts the frontend preview with `MOCK_TEST_API=false` and `API_BASE_URL=<backend preview URL>`
   (`integration.switched_to_live`) and checks the switch (`integration:health`: backend `/health`, the frontend's
   live runtime config). 2026-11-06: the live contract probe and the Playwright smoke were removed.
4. If not ready, keeps `MOCK_TEST_API=true` (`integration.kept_mocks`), records the reason and finishes the
   job as `COMPLETED_WITH_WARNINGS`.
"""

import asyncio
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

from src.configs import config
from src.modules.shared.domain.entities import ValidationRunEntity
from src.modules.shared.domain.enums import GenerationMode, LaneStatus, PreviewStatus

from ..backend.validation import CheckResult, ValidationOutcome, traced_check, write_report
from ..context import JobContext
from ..packaging import ArtifactWriter, build_contract_seed, build_seed, build_source_zip, write_frontend
from ..plugins import extended_spec
from ..previews import KINDS, wait_settled
from ..state import GenerationState, Outcome

CHECK_PREFIX = "integration:"
JUNIT_PATH = "test-results/e2e-junit.xml"
_PATH_PARAM = re.compile(r"\{([^}]+)\}")
NodeResult = tuple[dict[str, Any], dict[str, Any]]


def _optional_json(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text()) if path.is_file() else None


def _clip(value: Any, limit: int = 300) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    except Exception:
        text = str(value)
    return text[:limit]


async def package_lane_preview(state: GenerationState, ctx: JobContext, kind: str) -> None:
    """Packages a completed lane's source ZIP (and seed/OpenAPI for the backend) and starts its preview container
    during a dynamic run (Story 18.12: the moment the lane passes, whatever the other lane is doing). The frontend
    starts on the mock API, or on the live one when the backend preview already runs; `integrate` checks it later."""
    if ctx.mode != GenerationMode.DYNAMIC or ctx.previews is None:
        return
    if kind not in ctx.previews.runtimes:
        return
    if kind == "frontend":
        if not (state["options"].get("frontend") or {}).get("generatePreview", True):
            return
    elif not state["options"].get("deployPreview", True):
        return

    writer = ArtifactWriter(
        Path(config.artifact_root), ctx.generation_id, {a.name: a.id for a in ctx.store.artifacts(ctx.generation_id)}
    )
    if kind == "frontend":
        write_frontend(writer, ctx.workspace.frontend)
    else:
        project = ctx.workspace.project
        writer.write("backend.zip", "source", build_source_zip(project), "application/zip")
        plan = _optional_json(project / ".bga" / "plan.json") or {}
        if plan:
            writer.write_json("plan.json", "plan", plan)
        openapi = _optional_json(ctx.workspace.reports / "openapi.json")
        if openapi:
            writer.write_json("openapi.json", "openapi", openapi)
        contract_path = ctx.workspace.spec_dir / "contract.json"
        if contract_path.is_file() and plan:
            seed_blocks = build_contract_seed(json.loads(contract_path.read_text()), plan)
            if seed_blocks:
                writer.write_json("seed.json", "seed", seed_blocks)
        else:
            spec = _optional_json(project / ".bga" / "spec.json") or {}
            if plan and extended_spec(spec).get("seed"):  # the spec's seed, and the plugins' (10.2: demo users)
                generation = ctx.store.generation(ctx.generation_id)
                ts = (
                    generation.created_at.isoformat()
                    if generation and generation.created_at
                    else "1970-01-01T00:00:00+00:00"
                )
                writer.write_json("seed.json", "seed", build_seed(spec, plan, ctx.generation_id, ts))
        head_file = ctx.workspace.state / "backend-packaged-head"
        head_file.parent.mkdir(parents=True, exist_ok=True)
        head_sha = ctx.workspaces._git(ctx.workspace, "rev-parse", "HEAD", repo="project").strip()
        head_file.write_text(head_sha)
    ctx.store.replace_artifacts(ctx.generation_id, writer.written)
    # A backend start also reserves the frontend row's port: it holds both locks (backend, then frontend), unless
    # the frontend already has its port; then it never waits for a frontend build (Story 18.12).
    async with ctx.previews.locked(ctx.generation_id, *ctx.previews.lock_kinds(ctx.generation_id, "start", kind)):
        existing = ctx.store.preview(ctx.generation_id, kind)
        if existing is None or existing.status not in (PreviewStatus.STARTING, PreviewStatus.RUNNING):
            backend = ctx.store.preview(ctx.generation_id, "backend") if kind == "frontend" else None
            live = backend is not None and backend.status == PreviewStatus.RUNNING and backend.url
            override = {"mockApi": False, "apiBaseUrl": backend.url} if live else None
            await ctx.previews.start(ctx.generation_id, kind, options_override=override)


async def check_backend_ready(
    generation_id: str, previews: Any, wait_seconds: float = 0
) -> tuple[bool, str | None, str | None]:
    """Waits up to `wait_seconds` while the backend lane or its preview is still starting; ready once the lane is
    COMPLETED and its preview RUNNING with a URL (2026-11-06: no probes here, validation already proved the API)."""
    if previews is None:
        return False, "backend preview is not running", None
    store = previews.store
    deadline = time.monotonic() + max(0.0, float(wait_seconds))

    while True:
        generation = store.generation(generation_id)
        if generation is None:
            return False, "generation not found", None
        lane_status = (generation.lanes or {}).get("backend", LaneStatus.PENDING.value)
        if lane_status == LaneStatus.FAILED.value:
            return False, generation.error_summary or "backend lane failed", None
        if lane_status == LaneStatus.SKIPPED.value:
            return False, "backend lane was skipped", None
        if lane_status != LaneStatus.COMPLETED.value:
            if time.monotonic() < deadline:
                await asyncio.sleep(min(0.1, max(0.01, deadline - time.monotonic())))
                continue
            return False, "backend lane timed out before integration", None

        if "backend" not in previews.runtimes or not generation.options.get("deployPreview", True):
            return False, "backend preview is not running", None

        preview = store.preview(generation_id, "backend")
        if preview is None or preview.status == PreviewStatus.STARTING:
            if time.monotonic() < deadline:
                await asyncio.sleep(min(0.2, max(0.01, deadline - time.monotonic())))
                continue
            return False, ("backend preview did not become ready in time" if preview else
                           "backend preview is not running"), None  # fmt: skip
        if preview.status != PreviewStatus.RUNNING or not preview.url:
            return False, preview.error or f"backend preview is {preview.status}", None
        return True, None, preview.url


async def check_live_health(generation_id: str, previews: Any, backend_url: str) -> CheckResult:
    """Verifies the backend `/health` is 200 and the frontend preview's `/api/runtime-config` points to it."""
    started = time.monotonic()
    details: list[dict[str, Any]] = []
    code, body, _ = await previews.probe(generation_id, "GET", "/health", kind="backend")
    if code != 200:
        details.append(
            {
                "operation": "health",
                "field": "$status",
                "message": f"backend GET /health returned {code}",
                "response": _clip(body),
            }
        )
    fe_preview = previews.store.preview(generation_id, "frontend")
    if fe_preview is not None and fe_preview.status == PreviewStatus.RUNNING:
        fe_code, fe_cfg, _ = await previews.probe(generation_id, "GET", "/api/runtime-config", kind="frontend")
        if fe_code == 200 and isinstance(fe_cfg, dict):
            if fe_cfg.get("mockApi") is not False or fe_cfg.get("apiBaseUrl") != backend_url:
                details.append(
                    {
                        "page": "/api/runtime-config",
                        "operation": "runtime-config",
                        "field": "mockApi",
                        "message": f"frontend runtime-config did not switch to live: {_clip(fe_cfg)}",
                        "response": _clip(fe_cfg),
                    }
                )
    ok = not details
    return CheckResult(
        check="health",
        status="passed" if ok else "failed",
        duration_ms=int((time.monotonic() - started) * 1000),
        summary="backend /health and frontend live runtime-config ready" if ok else details[0]["message"],
        details=details,
    )


def _enforce_canonical_contract(ctx: JobContext) -> tuple[dict[str, Any], str]:
    """Story 14.1 AC 2: both lanes read `.bga/contract.json`; neither may change it."""
    canonical_path = ctx.workspace.spec_dir / "contract.json"
    raw = canonical_path.read_bytes()
    for target in (
        ctx.workspace.project / ".bga" / "contract.json",
        ctx.workspace.frontend / ".bga" / "contract.json",
    ):
        if target.parent.is_dir():
            target.write_bytes(raw)
    return json.loads(raw.decode()), hashlib.sha256(raw).hexdigest()


async def integrate(state: GenerationState, ctx: JobContext) -> NodeResult:
    """Node `integrate` (Stories 14.2, 14.3): waits for the backend preview, switches the frontend preview to live
    and checks the switch (`integration:health`)."""
    _, contract_sha256 = _enforce_canonical_contract(ctx)
    frontend_error = state.get("frontend_error")
    if frontend_error or ctx.lanes.get("frontend") == LaneStatus.FAILED.value:
        # Story 18.12: the backend still finished on its own (and its preview runs); nothing to switch.
        backend_error = state.get("backend_error") or ctx.backend_aborted_reason
        if ctx.lanes.get("backend") != LaneStatus.COMPLETED.value or backend_error:
            message = f"Both lanes failed. Frontend: {frontend_error or 'failed'}; backend: {backend_error or 'failed'}"
            await ctx.set_lane("integration", LaneStatus.SKIPPED, reason="both lanes failed")
            return {"outcome": Outcome.REPAIR_LIMIT, "error_summary": message[:2000]}, {
                "_status": "skipped",
                "reason": "both lanes failed",
            }
        reason = "frontend lane failed"
        await ctx.set_lane("integration", LaneStatus.SKIPPED, reason=reason)
        info = {"switchedToLive": False, "mockApi": None, "apiBaseUrl": "", "reason": reason}
        return {"integration": info, "integration_reason": reason}, {"_status": "skipped", "reason": reason}

    # In dynamic mode, backend preview was started early when backend lane completed.
    # If it wasn't started (e.g. preview worker delayed or retry), package and start it now.
    if ctx.previews is not None and ctx.lanes.get("backend") == LaneStatus.COMPLETED.value:
        existing_be = ctx.store.preview(ctx.generation_id, "backend")
        if existing_be is None or existing_be.status not in (PreviewStatus.STARTING, PreviewStatus.RUNNING):
            await package_lane_preview(state, ctx, "backend")

    wait_s = float(state["options"].get("integrationWaitSeconds", config.integration_wait_seconds))
    backend_error = state.get("backend_error") or ctx.backend_aborted_reason
    if ctx.lanes.get("backend") != LaneStatus.COMPLETED.value or backend_error:
        ok, reason, backend_url = (
            False,
            backend_error or f"backend lane is {ctx.lanes.get('backend', 'incomplete').lower()}",
            None,
        )
    else:
        ok, reason, backend_url = await check_backend_ready(ctx.generation_id, ctx.previews, wait_seconds=wait_s)
    if not ok or not backend_url:
        reason = reason or "backend preview is not running"
        if ctx.previews is not None and "frontend" in ctx.previews.runtimes:
            writer = ArtifactWriter(
                Path(config.artifact_root),
                ctx.generation_id,
                {a.name: a.id for a in ctx.store.artifacts(ctx.generation_id)},
            )
            write_frontend(writer, ctx.workspace.frontend)
            ctx.store.replace_artifacts(ctx.generation_id, writer.written)
            async with ctx.previews.locked(ctx.generation_id, *KINDS):  # switch_frontend may restart the backend
                fe_preview = ctx.store.preview(ctx.generation_id, "frontend")
                if fe_preview is None or fe_preview.status not in (PreviewStatus.STARTING, PreviewStatus.RUNNING):
                    await ctx.previews.start(
                        ctx.generation_id, "frontend", options_override={"mockApi": True, "apiBaseUrl": ""}
                    )
                elif fe_preview.mock_api is not True:
                    await ctx.previews.switch_frontend(ctx.generation_id, mock_api=True, api_base_url="")
        await ctx.emit("integration.kept_mocks", step="integrate", reason=reason, mockApi=True)
        await ctx.set_lane("integration", LaneStatus.SKIPPED, reason=reason)
        info = {"switchedToLive": False, "mockApi": True, "apiBaseUrl": "", "reason": reason}
        return {"integration": info, "integration_reason": reason}, {
            "_status": "skipped",
            "switchedToLive": False,
            "reason": reason,
        }

    assert ctx.previews is not None
    # The frontend usually runs already (on mocks, since its lane passed); a start sent over the bus may still be
    # building. A frontend that is not running yet starts directly on the live API (Story 18.8).
    await wait_settled(ctx.store, ctx.generation_id, "frontend", wait_s)
    writer = ArtifactWriter(
        Path(config.artifact_root), ctx.generation_id, {a.name: a.id for a in ctx.store.artifacts(ctx.generation_id)}
    )
    write_frontend(writer, ctx.workspace.frontend)
    ctx.store.replace_artifacts(ctx.generation_id, writer.written)
    async with ctx.previews.locked(ctx.generation_id, *KINDS):  # switch_frontend may restart the backend
        fe_preview = ctx.store.preview(ctx.generation_id, "frontend")
        if fe_preview is None or fe_preview.status not in (PreviewStatus.STARTING, PreviewStatus.RUNNING):
            await ctx.previews.start(
                ctx.generation_id, "frontend", options_override={"mockApi": False, "apiBaseUrl": backend_url}
            )
            fe_preview = ctx.store.preview(ctx.generation_id, "frontend")
        elif fe_preview.mock_api is not False:
            fe_preview = await ctx.previews.switch_frontend(ctx.generation_id, mock_api=False, api_base_url=backend_url)
    fe_preview = await wait_settled(ctx.store, ctx.generation_id, "frontend", wait_s, mock_api=False)
    await ctx.emit(
        "integration.switched_to_live",
        step="integrate",
        apiBaseUrl=backend_url,
        frontendUrl=fe_preview.url if fe_preview else None,
        contractSha256=contract_sha256,
        mockApi=False,
    )

    results: list[CheckResult] = []
    with traced_check(f"{CHECK_PREFIX}health") as slot:
        health_res = await check_live_health(ctx.generation_id, ctx.previews, backend_url)
        slot.append(health_res)
    results.append(health_res)

    for check in results:
        check_name = f"{CHECK_PREFIX}{check.check}"
        ctx.store.add_validation_run(
            ValidationRunEntity(
                generation_id=ctx.generation_id,
                attempt=1,
                check=check_name,
                status=check.status,
                started_at=check.started_at,
                duration_ms=check.duration_ms,
                details={"summary": check.summary, "items": check.details[:50], "output": check.output[-4000:]},
            )
        )
        await ctx.emit(
            "validation.check",
            step="integrate",
            status=check.status,
            check=check_name,
            summary=check.summary,
            durationMs=check.duration_ms,
            attempt=1,
        )

    outcome = ValidationOutcome(results=results, digest="", implicated_files=[])
    write_report(ctx.workspace.reports / "integration-validation.json", outcome)

    failed = [f"{CHECK_PREFIX}{r.check}" for r in results if r.status == "failed"]
    summary_map = {r.check: r.status for r in results}
    if failed:
        first_failed = next(r for r in results if r.status == "failed")
        first_item = first_failed.details[0] if first_failed.details else {}
        detail_msg = first_item.get("message") or first_failed.summary
        fail_reason = f"Live integration check failed ({first_failed.check}): {detail_msg}"
        await ctx.set_lane("integration", LaneStatus.FAILED, reason=fail_reason)
        info = {
            "switchedToLive": True,
            "mockApi": False,
            "apiBaseUrl": backend_url,
            "frontendUrl": fe_preview.url if fe_preview else None,
            "contractSha256": contract_sha256,
            "checks": summary_map,
            "failedChecks": failed,
            "reason": fail_reason,
        }
        return {"integration": info, "integration_reason": fail_reason}, {
            "_status": "failed",
            "switchedToLive": True,
            "apiBaseUrl": backend_url,
            "failedChecks": failed,
        }

    await ctx.set_lane("integration", LaneStatus.COMPLETED)
    info = {
        "switchedToLive": True,
        "mockApi": False,
        "apiBaseUrl": backend_url,
        "frontendUrl": fe_preview.url if fe_preview else None,
        "contractSha256": contract_sha256,
        "checks": summary_map,
        "failedChecks": [],
        "reason": None,
    }
    return {"integration": info, "integration_reason": None}, {
        "switchedToLive": True,
        "apiBaseUrl": backend_url,
        "failedChecks": [],
    }
