"""Site images (Epic 15): the asset registry a generated frontend renders from, and the drawings.

    src/assets/index.ts                         asset id → render mode, alt, aspect ratio, component or file
    src/components/assets/AssetImage.tsx        (overlay) renders each mode, `data-bga-asset="<id>"`
    src/assets/svg/<id>.svg                     a drawing (`source: "generate"`, Story 15.2)
    src/components/assets/generated/<Name>.tsx  its React component (svg_assets.svg_to_tsx)

`frontend:assets` (Story 15.3) checks every drawing before the build (svg_assets.py rules); a drawing still failing
after `FRONTEND_ASSET_REPAIR_LIMIT` repairs, or when the job has no repair attempt left, falls back to its
placeholder (`fallback` in the plan, warning FE_ASSET_FALLBACK), so an asset never fails the frontend lane.

The plan lists every asset with its render mode (frontend_planner.py). An SVG the engine has not drawn yet (or that
fell back, 15.3) and an upload not yet copied render as the placeholder panel, so the registry is always buildable.

`generate_assets` (between scaffold and generate) draws every generated asset of a job in one engine call, in a
scratch directory holding only the request: only the requested SVG files come back. Drawings are cached by what
they were drawn from (key below), not by theme colours, which they only reference as variables.
"""

import asyncio
import hashlib
import json
import shutil
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from src.configs import config, get_logger
from src.configs.config import uploads_dir
from src.images import generate_single_photo, get_image_generator

from .asset_registry import ASSETS_FILE, assets_ts
from .context import EngineFailure, JobContext
from .frontend_planner import asset_component, dump_frontend_plan
from .frontend_scaffold import drop_owned, update_owned
from .state import GenerationState
from .svg_assets import THEME_TOKENS, VIEWBOXES, check_component, check_svg, svg_to_tsx
from .validation import CheckResult

logger = get_logger(__name__)
PROMPT_VERSION = "v1"  # generate_assets
REQUEST_FILE = ".bga/assets.json"
PLAN_REF = ".bga/frontend-plan.json"
# What the engine adapters write into a working directory themselves (skills, rules, the request).
ENGINE_MANAGED = (".bga/", ".claude/", ".agents/", "AGENTS.md", "CLAUDE.md", "GEMINI.md")

# -- drawings (Story 15.2) ---------------------------------------------------------------------------------------------


def asset_key(asset: dict[str, Any], engine: str) -> str:
    canonical = {
        "promptVersion": PROMPT_VERSION,
        "engine": engine,
        "kind": asset["kind"],
        "prompt": " ".join((asset.get("prompt") or "").split()),
        "style": " ".join((asset.get("style") or "").split()),
        "aspectRatio": asset["aspectRatio"],
    }
    return hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()


def cached_svg(key: str) -> Path:
    return Path(config.artifact_root) / "asset-cache" / f"{key}.svg"


def convert_drawing(project: Path, asset: dict[str, Any]) -> bool:
    """Writes the component of a drawn SVG and marks it drawn; False (left as a placeholder) when the SVG is missing
    or breaks the safe rule, which the `frontend:assets` check then reports (15.3)."""
    svg = project / asset["file"]
    asset["drawn"] = False
    if not svg.is_file():
        return False
    text = svg.read_text()
    if any(issue.rule == "safe" for issue in check_svg(text, asset["aspectRatio"])):
        return False
    target = project / asset["component"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(svg_to_tsx(text, asset, asset_component(asset["id"])))
    asset["drawn"] = True
    asset["sha256"] = hashlib.sha256(text.encode()).hexdigest()
    return True


def write_registry(project: Path, plan: dict[str, Any]) -> list[str]:
    """Rewrites the registry and the plan after the drawings changed; returns the owned files to record."""
    assets_file = project / ASSETS_FILE
    assets_file.parent.mkdir(parents=True, exist_ok=True)
    assets_file.write_text(assets_ts(plan))
    plan_ref = project / PLAN_REF
    plan_ref.parent.mkdir(parents=True, exist_ok=True)
    plan_ref.write_text(dump_frontend_plan(plan))
    owned = [ASSETS_FILE]
    for asset in plan.get("assets", []):
        if asset["render"] == "svg-component" and asset.get("drawn"):
            owned += [asset["file"], asset["component"]]
        elif asset["render"] == "public-file" and asset.get("src"):
            owned.append(asset["file"])
        elif asset["render"] == "photo" and asset.get("generated") and asset.get("file"):
            owned.append(asset["file"])
    update_owned(project, owned)
    return owned


def _out_of_scope(scratch: Path, requested: set[str]) -> list[str]:
    written = (path.relative_to(scratch).as_posix() for path in scratch.rglob("*") if path.is_file())
    return sorted(p for p in written if p not in requested and not p.startswith(ENGINE_MANAGED))


async def _run_svgs(ctx: JobContext, project: Path, wanted: list[dict[str, Any]]) -> tuple[int, int, int]:
    cached: set[str] = set()
    misses = []
    for asset in wanted:
        asset["cacheKey"] = asset_key(asset, ctx.engine.name)
        hit = cached_svg(asset["cacheKey"])
        if hit.is_file():
            target = project / asset["file"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(hit, target)
            cached.add(asset["id"])
        else:
            misses.append(asset)
    engine_calls = 0
    if misses:
        engine_calls = await _draw(ctx, project, misses)
    drawn = 0
    for asset in wanted:
        asset["cached"] = asset["id"] in cached
        if convert_drawing(project, asset):
            drawn += 1
            await ctx.emit("frontend.asset.ready", step="generate_assets", id=asset["id"], cached=asset["cached"])
        else:
            await ctx.emit("frontend.asset.missing", step="generate_assets", id=asset["id"], file=asset["file"])
    return drawn, len(cached), engine_calls


async def _run_photos(
    ctx: JobContext, project: Path, wanted: list[dict[str, Any]]
) -> tuple[list[dict[str, str]], int, int]:
    generator = get_image_generator()
    sem = asyncio.Semaphore(config.image_concurrency)
    image_records = []
    photo_fallbacks: list[dict[str, str]] = []
    photos_ready = 0
    photos_cached = 0

    async def _process_photo(asset: dict[str, Any]) -> None:
        nonlocal photos_ready, photos_cached
        target_path = project / asset["file"]
        ok, record, fallback_reason = await generate_single_photo(
            asset,
            target_path,
            generator=generator,
            generation_id=ctx.generation_id,
            node_run_id=getattr(ctx, "current_node_run_id", None),
            semaphore=sem,
        )
        image_records.append(record)
        if ok:
            is_cached = record.status == "cached"
            if is_cached:
                photos_cached += 1
            photos_ready += 1
            await ctx.emit(
                "frontend.photo.ready",
                step="generate_assets",
                id=asset["id"],
                cached=is_cached,
                durationMs=record.duration_ms,
            )
        else:
            asset["fallback"] = fallback_reason
            asset["generated"] = False
            photo_fallbacks.append({"id": asset["id"], "reason": fallback_reason or "failed"})
            await ctx.emit("frontend.photo.fallback", step="generate_assets", id=asset["id"], reason=fallback_reason)

    tasks = [_process_photo(asset) for asset in wanted]
    if tasks:
        await asyncio.gather(*tasks)

    if image_records:
        ctx.store.add_image_calls(image_records)

    return photo_fallbacks, photos_ready, photos_cached


async def generate_assets(state: GenerationState, ctx: JobContext) -> tuple[dict[str, Any], dict[str, Any]]:
    """Stories 15.2, 19.2: draw SVGs and generate AI photos in parallel, caching both."""
    plan = json.loads(ctx.frontend_path(state["frontend_plan_ref"]).read_text())
    wanted_svgs = [asset for asset in plan.get("assets", []) if asset["render"] == "svg-component"]
    wanted_photos = [asset for asset in plan.get("assets", []) if asset["render"] == "photo"]

    # Story 19.2 step 7a: Missing uploads with a prompt are remade as photos
    for asset in plan.get("assets", []):
        if asset["render"] == "public-file" and not asset.get("src") and asset.get("prompt"):
            asset["render"] = "photo"
            asset["file"] = f"public/assets/{asset['id']}.webp"
            asset["src"] = f"/assets/{asset['id']}.webp"
            asset["generated"] = False
            wanted_photos.append(asset)
            await ctx.emit("frontend.photo.remade", step="generate_assets", id=asset["id"], upload=asset.get("upload"))

    if not wanted_svgs and not wanted_photos:
        return {}, {"_status": "skipped", "reason": "no generated assets or photos"}

    project = ctx.workspace.frontend

    # Run drawings and photos concurrently
    svg_coro = _run_svgs(ctx, project, wanted_svgs) if wanted_svgs else None
    photo_coro = _run_photos(ctx, project, wanted_photos) if wanted_photos else None

    drawn_svgs, cached_svgs, engine_calls = 0, 0, 0
    photo_fallbacks: list[dict[str, str]] = []
    photos_ready, photos_cached = 0, 0

    if svg_coro and photo_coro:
        (drawn_svgs, cached_svgs, engine_calls), (photo_fallbacks, photos_ready, photos_cached) = await asyncio.gather(
            svg_coro, photo_coro
        )
    elif svg_coro:
        drawn_svgs, cached_svgs, engine_calls = await svg_coro
    elif photo_coro:
        photo_fallbacks, photos_ready, photos_cached = await photo_coro

    async with ctx.frontend_plan_lock:
        current_plan = json.loads(ctx.frontend_path(PLAN_REF).read_text())
        current_plan["assets"] = plan["assets"]
        write_registry(project, current_plan)

    summary = {
        "assets": len(wanted_svgs) + len(wanted_photos),
        "drawn": drawn_svgs,
        "cacheHits": cached_svgs + photos_cached,
        "engineCalls": engine_calls,
    }
    if wanted_photos:
        summary["photos"] = len(wanted_photos)
        summary["photosReady"] = photos_ready
    await ctx.emit("frontend.assets.done", step="generate_assets", **summary)
    update: dict[str, Any] = {}
    if photo_fallbacks:
        known = state.get("asset_fallbacks") or []
        update["asset_fallbacks"] = [*known, *photo_fallbacks]
    return update, summary


async def _draw_one(ctx: JobContext, project: Path, asset: dict[str, Any]) -> bool:
    """One engine call in its own scratch directory (scratch/assets-<id>)."""
    scratch = ctx.workspace.root / "scratch" / f"assets-{asset['id']}"
    shutil.rmtree(scratch, ignore_errors=True)
    (scratch / ".bga").mkdir(parents=True)
    request = [
        {
            "id": asset["id"],
            "kind": asset["kind"],
            "prompt": asset["prompt"],
            "style": asset.get("style"),
            "aspectRatio": asset["aspectRatio"],
            "viewBox": VIEWBOXES[asset["aspectRatio"]],
            "file": asset["file"],
            "decorative": asset["decorative"],
        }
    ]
    (scratch / REQUEST_FILE).write_text(json.dumps({"assets": request}, indent=2) + "\n")
    prompt = ctx.prompts.render(
        "generate_assets",
        PROMPT_VERSION,
        assets=request,
        tokens=THEME_TOKENS,
        request_path=REQUEST_FILE,
        max_kb=30,
    )
    async with ctx.engine_slots:
        try:
            await ctx.run_engine(
                "generate_assets", "generate_assets", prompt, repo="frontend", workdir_override=scratch
            )
        except EngineFailure as exc:
            logger.warning(
                "asset drawing failed",
                extra={"generation_id": ctx.generation_id, "asset_id": asset["id"], "error": str(exc)},
            )
            await ctx.emit("frontend.asset.failed", step="generate_assets", id=asset["id"], error=str(exc)[:500])
            shutil.rmtree(scratch, ignore_errors=True)
            return False

    requested = {asset["file"]}
    extra = _out_of_scope(scratch, requested)
    if extra:
        await ctx.emit("frontend.asset.out_of_scope", step="generate_assets", id=asset["id"], files=extra[:50])
    source = scratch / asset["file"]
    if source.is_file():
        target = project / asset["file"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if not check_svg(source.read_text(), asset["aspectRatio"]):
            cache = cached_svg(asset["cacheKey"])
            cache.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, cache)
    shutil.rmtree(scratch, ignore_errors=True)
    return True


async def _draw(ctx: JobContext, project: Path, misses: list[dict[str, Any]]) -> int:
    """One engine call per missing drawing, running concurrently up to ctx.engine_slots."""
    tasks = [asyncio.create_task(_draw_one(ctx, project, asset)) for asset in misses]
    try:
        await asyncio.gather(*tasks)
    except BaseException:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
    return len(misses)


# -- checks and fallback (Story 15.3) ----------------------------------------------------------------------------------


def drawing_issues(project: Path, asset: dict[str, Any]) -> list[dict[str, str]]:
    """What is wrong with one asset's drawing and its component (empty: nothing, or nothing drawn)."""
    svg = project / asset["file"]
    if asset.get("fallback") or not svg.is_file():
        return []
    issues = [issue.as_dict(asset["file"]) for issue in check_svg(svg.read_text(), asset["aspectRatio"])]
    component = project / asset["component"]
    if asset.get("drawn") and component.is_file():
        issues += [issue.as_dict(asset["component"]) for issue in check_component(component.read_text())]
    return [{**issue, "asset": asset["id"]} for issue in issues]


def assets_check(project: Path, plan: dict[str, Any]) -> CheckResult:
    """`frontend:assets`: the drawings are safe, valid, themed and accessible; fallbacks and unused assets are
    warnings (`severity`), which never fail the check."""
    started = time.monotonic()
    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for asset in plan.get("assets", []):
        if asset["render"] == "svg-component":
            failures += drawing_issues(project, asset)
            if asset.get("fallback"):
                warnings.append(
                    {
                        "asset": asset["id"],
                        "file": asset["file"],
                        "rule": "fallback",
                        "code": "FE_ASSET_FALLBACK",
                        "severity": "warning",
                        "message": f"'{asset['id']}' shows its placeholder: {asset['fallback']}",
                    }
                )
        elif asset["render"] == "photo":
            if not asset.get("generated") or asset.get("fallback"):
                reason = asset.get("fallback") or "photo was not generated"
                warnings.append(
                    {
                        "asset": asset["id"],
                        "file": asset.get("file", f"public/assets/{asset['id']}.webp"),
                        "rule": "fallback",
                        "code": "FE_PHOTO_FALLBACK",
                        "severity": "warning",
                        "message": f"'{asset['id']}' shows its placeholder: {reason}",
                    }
                )
            else:
                photo_file = project / asset["file"]
                if not photo_file.is_file():
                    failures.append(
                        {
                            "asset": asset["id"],
                            "file": asset["file"],
                            "rule": "exists",
                            "severity": "error",
                            "message": f"'{asset['id']}' file '{asset['file']}' is missing",
                        }
                    )
                elif photo_file.suffix.lower() != ".webp":
                    failures.append(
                        {
                            "asset": asset["id"],
                            "file": asset["file"],
                            "rule": "format",
                            "severity": "error",
                            "message": f"'{asset['id']}' file must be WebP, got '{photo_file.name}'",
                        }
                    )
        if not asset.get("routes"):
            warnings.append(
                {"asset": asset["id"], "rule": "referenced", "severity": "warning",
                 "message": f"'{asset['id']}' is declared but no page uses it"}
            )  # fmt: skip
    drawings = sum(1 for asset in plan.get("assets", []) if asset["render"] == "svg-component")
    photos = sum(1 for asset in plan.get("assets", []) if asset["render"] == "photo")
    if failures:
        summary = f"{len(failures)} asset problem(s) in {len({f['asset'] for f in failures})} asset(s)"
    else:
        fell_back = sum(1 for w in warnings if w["rule"] == "fallback")
        parts = []
        if drawings:
            parts.append(f"{drawings} drawing(s)")
        if photos:
            parts.append(f"{photos} photo(s)")
        count_desc = " and ".join(parts) if parts else f"{drawings} drawing(s)"
        summary = f"{count_desc} checked" + (f", {fell_back} on their placeholder" if fell_back else "")
    return CheckResult(
        check="assets",
        status="failed" if failures else "passed",
        duration_ms=int((time.monotonic() - started) * 1000),
        summary=summary,
        details=failures + warnings,
    )


def fall_back(project: Path, plan: dict[str, Any], reasons: dict[str, str]) -> None:
    """Puts these drawings back on their placeholder: the files go, the registry no longer imports them."""
    removed = []
    for asset in plan.get("assets", []):
        if asset["id"] in reasons:
            asset["fallback"] = reasons[asset["id"]]
            asset["drawn"] = False
            for relative in (asset["file"], asset["component"]):
                (project / relative).unlink(missing_ok=True)
                removed.append(relative)
    drop_owned(project, removed)
    write_registry(project, plan)


def due_fallbacks(project: Path, plan: dict[str, Any], repair_limit: int, attempts_left: bool) -> dict[str, str]:
    """Drawings that still fail after their repairs (or with no repair attempt left), with the first problem."""
    due = {}
    for asset in plan.get("assets", []):
        if asset["render"] != "svg-component" or asset.get("fallback"):
            continue
        issues = drawing_issues(project, asset)
        if issues and (asset.get("repairs", 0) >= repair_limit or not attempts_left):
            due[asset["id"]] = f"{issues[0]['rule']}: {issues[0]['message']}"
    return due


def redraw_after_repair(project: Path, plan: dict[str, Any], implicated: list[str]) -> list[str]:
    """After `repair_frontend`: counts a repair for each drawing it was asked to fix and converts every drawing
    again (the engine may have changed the SVG); returns the ids repaired."""
    repaired = []
    for asset in plan.get("assets", []):
        if asset["render"] != "svg-component" or asset.get("fallback"):
            continue
        if asset["file"] in implicated or asset.get("component") in implicated:
            asset["repairs"] = asset.get("repairs", 0) + 1
            repaired.append(asset["id"])
        convert_drawing(project, asset)
    write_registry(project, plan)
    return repaired


# -- uploads (Story 15.4) ----------------------------------------------------------------------------------------------


def copy_uploads(project: Path, plan: dict[str, Any], find_upload: Callable[[str], Any]) -> list[str]:
    """Copies each uploaded asset to `public/assets/<asset id>.<ext>` with its size (no layout shift) and hash;
    returns the ids whose upload is gone (deleted since the generation was created), left as placeholders."""
    missing = []
    for asset in plan.get("assets", []):
        if asset["render"] != "public-file":
            continue
        upload = find_upload(asset["upload"])
        source = Path(uploads_dir()) / upload.relative_path if upload is not None else None
        if source is None or not source.is_file():
            missing.append(asset["id"])
            continue
        relative = f"public/assets/{asset['id']}.{upload.extension}"
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        asset |= {
            "file": relative,
            "src": f"/assets/{asset['id']}.{upload.extension}",
            "width": upload.width,
            "height": upload.height,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        }
    return missing
