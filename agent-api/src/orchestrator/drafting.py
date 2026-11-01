"""Requirement drafting (Stories 2.4, 12.4): a requirement (or an imported site) → draft spec(s) for review.

A draft runs on the worker, outside the generation graph: one engine call in a scratch directory writes the spec
file(s) and `notes.json`; they are validated (BackendSpec 2.2, FrontendSpec 12.1, and in dynamic mode the pair's
consistency 12.5) and repaired by the engine a bounded number of times. A draft that is still invalid ends as
NEEDS_REVIEW with its errors; it is never submitted. Each engine call is recorded on the draft (`usage`) and traced.

Static and dynamic drafts from a requirement get a design direction (Story 12.6): the engine sees three ranked
briefs (`.bga/design.md`) and names one in its notes; the theme, the home page order and the hero layout are then
filled from the design data, and the three directions are kept on the draft (`design`) for the review.

Drafts show no placeholders (Epic 15): an image the engine left as a placeholder is turned into a drawing
(`source: "generate"`, prompt from its alt text, style from the direction), up to the generated-image limit.
"""

import asyncio
import hashlib
import io
import json
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image

from src.configs import config, get_logger
from src.configs.config import uploads_dir
from src.engines import EngineRegistry, PromptLibrary
from src.engines.port import EngineContext, EngineRequest, EngineResult, EngineStatus
from src.engines.prompts import RenderedPrompt
from src.images.factory import get_image_generator, photos_enabled
from src.images.service import generate_single_photo
from src.libs.ids.ulid import new_upload_id
from src.modules.shared.domain.backend_spec import (
    SpecIssue,
    ValidationReport,
    spec_json_schema,
    validate_spec_data,
)
from src.modules.shared.domain.entities import ImageCallEntity, SpecDraftEntity, UploadEntity
from src.modules.shared.domain.enums import GenerationMode, GenerationStatus, SpecDraftStatus, SpecSource
from src.modules.shared.domain.frontend_spec import (
    BUILTIN_SECTIONS,
    LAYOUT_SECTIONS,
    SECTION_PROPS,
    add_manage_area,
    autofix_frontend_spec,
    frontend_spec_json_schema,
    validate_frontend_spec_data,
)
from src.modules.shared.domain.frontend_spec.assets import MAX_GENERATED_ASSETS, SVG_KINDS, source_kind
from src.modules.shared.domain.generation_modes import initial_lanes
from src.modules.shared.domain.schema_digest import schema_digest

from . import tracing
from .checks.consistency import check_spec_pair
from .contract import build_contract
from .design_direction import (
    PHOTO_STYLES_BY_PRESET,
    apply_direction,
    brief_markdown,
    design_notes,
    directions,
    pick,
    with_brand,
)
from .store import JobStore

logger = get_logger(__name__)

INPUTS = ".bga"
BACKEND_FILE = "backend-spec.json"
FRONTEND_FILE = "frontend-spec.json"
NOTES_FILE = "notes.json"
MAX_REPAIR_ERRORS = 50
# Examples handed to the engine, relative to EXAMPLES_DIR (the repo's `examples/`).
EXAMPLES = {
    "backend": "specs/shop.json",
    "static": "frontend-specs/static-landing.json",
    "dynamic": "frontend-specs/shop-dynamic.json",
}


class DraftFailed(Exception):
    pass


# -- inputs --------------------------------------------------------------------------------------------------------


def section_catalogue() -> str:
    """The built-in sections the drafter should prefer (Story 17.1), with their typed content fields."""
    lines = [
        "# Built-in sections",
        "",
        'Use them as `{"id", "component": "<Name>", "content": {...}}`; the full content types are in the',
        "FrontendSpec schema (`$defs`). Data sections take `data` instead of (or as well as) `content`: in a static",
        "site `data.collection` names a `content` collection, in a dynamic app `data.operationId` names an API",
        "operation. These render without any model call; prefer them to custom components.",
        "",
    ]
    for name, model in SECTION_PROPS.items():
        if name in LAYOUT_SECTIONS:
            continue
        fields = ", ".join(model.model_json_schema(by_alias=True).get("properties", {}))
        lines.append(f"- **{name}**: {BUILTIN_SECTIONS[name]['description']}. Content: {fields or 'none'}.")
    lines += [
        "",
        "# Layout nodes",
        "",
        "They hold other sections in `children` (nesting depth 3 at most) and only arrange them.",
        "",
    ]
    for name in sorted(LAYOUT_SECTIONS):
        fields = ", ".join(SECTION_PROPS[name].model_json_schema(by_alias=True).get("properties", {}))
        lines.append(f"- **{name}**: {BUILTIN_SECTIONS[name]['description']}. Content: {fields or 'none'}.")
    return "\n".join(lines) + "\n"


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def _copy_example(examples_dir: Path, name: str, target: Path) -> None:
    source = examples_dir / name
    if not source.is_file():
        raise DraftFailed(f"Example spec missing: {source} (set EXAMPLES_DIR)")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def write_inputs(
    work: Path, draft: SpecDraftEntity, examples_dir: Path, design: list[dict[str, Any]] | None = None
) -> dict[str, str]:
    """Writes the engine's inputs under `.bga/` and returns the prompt context (paths relative to `work`)."""
    inputs = work / INPUTS
    mode = GenerationMode(draft.mode)
    _write_json(
        inputs / "draft.json",
        {
            "source": draft.source,
            "mode": mode,
            "requirementFormat": draft.requirement_format,
            "requirementFileName": draft.requirement_file_name,
        },
    )
    context: dict[str, Any] = {"mode": str(mode), "source": str(draft.source), "notes_path": NOTES_FILE}
    if draft.source == SpecSource.REQUIREMENT:
        name = "requirement.md" if draft.requirement_format == "markdown" else "requirement.txt"
        (inputs / name).write_text(draft.requirement_text or "")
        context |= {"requirement_text": draft.requirement_text, "requirement_format": draft.requirement_format}
    if mode in (GenerationMode.BACKEND, GenerationMode.DYNAMIC):
        _write_json(inputs / "backend-spec.schema.json", spec_json_schema())
        (inputs / "backend-spec.schema.md").write_text(schema_digest(spec_json_schema(), "BackendSpec"))
        _copy_example(examples_dir, EXAMPLES["backend"], inputs / "examples" / "backend-spec.json")
        context |= {
            "schema_path": f"{INPUTS}/backend-spec.schema.json",
            "schema_digest_path": f"{INPUTS}/backend-spec.schema.md",
            "example_path": f"{INPUTS}/examples/backend-spec.json",
            "backend_schema_path": f"{INPUTS}/backend-spec.schema.json",
            "backend_schema_digest_path": f"{INPUTS}/backend-spec.schema.md",
            "backend_example_path": f"{INPUTS}/examples/backend-spec.json",
            "output_spec_path": BACKEND_FILE,
            "output_backend_path": BACKEND_FILE,
        }
    if mode in (GenerationMode.STATIC, GenerationMode.DYNAMIC):
        _write_json(inputs / "frontend-spec.schema.json", frontend_spec_json_schema())
        (inputs / "frontend-spec.schema.md").write_text(schema_digest(frontend_spec_json_schema(), "FrontendSpec"))
        _copy_example(examples_dir, EXAMPLES[str(mode)], inputs / "examples" / "frontend-spec.json")
        (inputs / "sections.md").write_text(section_catalogue())
        context |= {
            "frontend_schema_path": f"{INPUTS}/frontend-spec.schema.json",
            "frontend_schema_digest_path": f"{INPUTS}/frontend-spec.schema.md",
            "frontend_example_path": f"{INPUTS}/examples/frontend-spec.json",
            "sections_path": f"{INPUTS}/sections.md",
            "output_frontend_path": FRONTEND_FILE,
            "design_path": None,
            "photos_enabled": photos_enabled(),
            "max_photos": config.frontend_max_photos,
        }
    if design:
        (inputs / "design.md").write_text(brief_markdown(design))
        context["design_path"] = f"{INPUTS}/design.md"
    if draft.source == SpecSource.FRONTEND:
        _write_json(inputs / "base-spec.json", draft.inputs.get("baseSpec"))
        _write_json(inputs / "site.json", draft.inputs.get("siteJson"))
        context |= {"base_spec_path": f"{INPUTS}/base-spec.json", "site_json_path": f"{INPUTS}/site.json"}
    return context


# -- checks --------------------------------------------------------------------------------------------------------


@dataclass
class DraftCheck:
    backend_spec: dict[str, Any] | None = None
    frontend_spec: dict[str, Any] | None = None
    reports: dict[str, ValidationReport] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return all(report.valid for report in self.reports.values())

    def repair_errors(self) -> list[dict[str, Any]]:
        """The errors to hand to `repair_spec`, each with the file it is in and a focused excerpt."""
        files = {"backend": BACKEND_FILE, "frontend": FRONTEND_FILE, "pair": FRONTEND_FILE}
        specs = {
            BACKEND_FILE: self.backend_spec,
            FRONTEND_FILE: self.frontend_spec,
        }
        errors = []
        for key, report in self.reports.items():
            filename = files[key]
            doc = specs.get(filename)
            for issue in report.errors:
                item = {"file": filename, **issue.model_dump(mode="json", exclude={"severity"}, exclude_none=True)}
                if doc is not None:
                    item["excerpt"] = build_excerpt(doc, issue.path)
                errors.append(item)
        return errors[:MAX_REPAIR_ERRORS]

    def validation(self) -> dict[str, Any]:
        return {key: report.model_dump(mode="json") for key, report in self.reports.items()}


def build_excerpt(doc: Any, path: str, max_chars: int = 1500) -> str:
    """Returns a JSON string containing the value at `path` and its parent, trimmed to ~max_chars."""
    if doc is None:
        return ""
    tokens = [t.replace("~1", "/").replace("~0", "~") for t in path.strip("/").split("/") if t]
    current = doc
    parent = None
    matched_tokens: list[str] = []
    for token in tokens:
        if isinstance(current, dict) and token in current:
            parent = current
            current = current[token]
            matched_tokens.append(token)
        elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
            parent = current
            current = current[int(token)]
            matched_tokens.append(token)
        else:
            parent = current
            current = None
            break
    data: dict[str, Any] = {}
    if parent is not None:
        if current is None:
            parent_path = "/" + "/".join(matched_tokens) if matched_tokens else "/"
        else:
            parent_path = "/" + "/".join(matched_tokens[:-1]) if len(matched_tokens) > 1 else "/"
        data[f"parent ({parent_path})"] = parent
    if current is not None:
        data[f"target ({path or '/'})"] = current
    if not data and doc is not None:
        data["root"] = doc
    text = json.dumps(data, indent=2, ensure_ascii=False)
    if len(text) > max_chars:
        return text[:max_chars] + "... [truncated]"
    return text


def _load(path: Path) -> tuple[Any, SpecIssue | None]:
    if not path.is_file():
        return None, SpecIssue(code="DRAFT_FILE_MISSING", path="", message=f"The draft has no {path.name}")
    try:
        return json.loads(path.read_text()), None
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return None, SpecIssue(code="JSON_MALFORMED", path="", message=f"{path.name} is not valid JSON: {exc}")


def check_draft(work: Path, mode: GenerationMode) -> DraftCheck:
    check = DraftCheck()
    backend_normalized = frontend_normalized = None
    if mode in (GenerationMode.BACKEND, GenerationMode.DYNAMIC):
        data, issue = _load(work / BACKEND_FILE)
        if issue is not None:
            check.reports["backend"] = ValidationReport.from_issues([issue], None)
        else:
            result = validate_spec_data(data)
            check.backend_spec, check.reports["backend"] = data, result.report
            backend_normalized = result.normalized
    if mode in (GenerationMode.STATIC, GenerationMode.DYNAMIC):
        data, issue = _load(work / FRONTEND_FILE)
        if issue is not None:
            check.reports["frontend"] = ValidationReport.from_issues([issue], None)
        else:
            result = validate_frontend_spec_data(data)
            report = result.report
            declared = (data.get("project") or {}).get("mode") if isinstance(data, dict) else None
            if result.normalized is not None and declared != mode:
                mismatch = SpecIssue(
                    code="MODE_MISMATCH",
                    path="/project/mode",
                    message=f"The draft is for a '{mode}' site but the spec says '{declared}'",
                    hint=f'Set "project": {{"mode": "{mode}"}}',
                )
                report = ValidationReport.from_issues([mismatch, *report.errors, *report.warnings], report.spec_version)
            check.frontend_spec, check.reports["frontend"] = data, report
            frontend_normalized = result.normalized if report.valid else None
    if mode == GenerationMode.DYNAMIC and backend_normalized is not None and frontend_normalized is not None:
        issues = check_spec_pair(frontend_normalized, backend_normalized)
        check.reports["pair"] = ValidationReport.from_issues(issues, check.reports["frontend"].spec_version)
    return check


def read_notes(work: Path, mode: GenerationMode) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """`notes.json` → (assumptions, unresolved) as `{path, message, suggestion?, spec?}`; tolerant of what the
    engine wrote (`reason` for `message`, missing paths), since notes are advisory."""
    data, issue = _load(work / NOTES_FILE)
    if issue is not None or not isinstance(data, dict):
        missing = {"path": "", "message": "The draft came without notes; review every part of it", "spec": None}
        return [missing], []
    default_spec = {GenerationMode.BACKEND: "backend", GenerationMode.STATIC: "frontend"}.get(mode)

    def notes(key: str) -> list[dict[str, Any]]:
        out = []
        for item in data.get(key) or []:
            if isinstance(item, str):
                item = {"message": item}
            if not isinstance(item, dict):
                continue
            message = item.get("message") or item.get("reason")
            if not isinstance(message, str) or not message.strip():
                continue
            spec = item.get("spec") if item.get("spec") in ("backend", "frontend") else default_spec
            suggestion = item.get("suggestion")
            out.append(
                {
                    "path": str(item.get("path") or ""),
                    "message": message.strip(),
                    "suggestion": suggestion if isinstance(suggestion, str) else None,
                    "spec": spec,
                }
            )
        return out

    return notes("assumptions"), notes("unresolved")


def draft_directions(draft: SpecDraftEntity) -> list[dict[str, Any]]:
    """The ranked design directions for a static or dynamic draft from a requirement (none otherwise)."""
    mode = GenerationMode(draft.mode)
    if mode == GenerationMode.BACKEND or draft.source != SpecSource.REQUIREMENT or not draft.requirement_text:
        return []
    return directions(draft.requirement_text)


def apply_design(work: Path, found: list[dict[str, Any]]) -> dict[str, Any]:
    """Fills the drafted FrontendSpec from the brief the engine named in `notes.json` (`design.productType`, else
    the first), with the requirement's brand colours and fonts on top; returns what the draft keeps (`design`)."""
    notes, _ = _load(work / NOTES_FILE)
    choice = notes.get("design") if isinstance(notes, dict) and isinstance(notes.get("design"), dict) else {}
    brand = {"colors": choice.get("brandColors"), "fonts": choice.get("brandFonts")}
    kept = [with_brand(item, brand) for item in found]
    selected = pick(kept, choice.get("productType"))
    spec, issue = _load(work / FRONTEND_FILE)
    if issue is None and isinstance(spec, dict) and isinstance(spec.get("pages"), list):
        _write_json(work / FRONTEND_FILE, apply_direction(spec, kept[selected]))
    return {"selected": selected, "directions": kept}


def draw_images(work: Path, chosen: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Turns the drafted FrontendSpec's placeholder images into photos (when enabled and under cap) or drawings
    (prompt from the alt text, style from the design direction), up to MAX_GENERATED_ASSETS; returns assumptions."""
    spec, issue = _load(work / FRONTEND_FILE)
    if issue is not None or not isinstance(spec, dict) or not isinstance(spec.get("assets"), list):
        return []
    assets = [asset for asset in spec["assets"] if isinstance(asset, dict)]
    drawn = sum(source_kind(str(asset.get("source") or "placeholder")) == "generate" for asset in assets)
    photos_on = photos_enabled()
    max_photos = config.frontend_max_photos
    photos_count = sum(
        1
        for a in assets
        if a.get("source") == "photo" or (str(a.get("source") or "").startswith("upload:") and bool(a.get("prompt")))
    )
    photo_style = (chosen or {}).get("photoStyle") or PHOTO_STYLES_BY_PRESET.get(
        (chosen or {}).get("theme", {}).get("style", "minimal"), PHOTO_STYLES_BY_PRESET["minimal"]
    )
    style = f"{chosen['style']}, flat vector shapes" if chosen and "style" in chosen else None
    converted_photos: list[str] = []
    converted_drawings: list[str] = []
    skipped: list[str] = []
    for asset in assets:
        if source_kind(str(asset.get("source") or "placeholder")) != "placeholder":
            continue
        if not isinstance(asset.get("id"), str):
            continue
        kind = asset.get("kind") or "image"
        if photos_on and kind == "image" and photos_count < max_photos:
            asset["source"] = "photo"
            asset["prompt"] = asset.get("prompt") or asset.get("alt") or asset["id"].replace("-", " ")
            if photo_style and not asset.get("style"):
                asset["style"] = photo_style
            photos_count += 1
            converted_photos.append(asset["id"])
        elif drawn < MAX_GENERATED_ASSETS and kind in SVG_KINDS:
            asset["source"] = "generate"
            asset["prompt"] = asset.get("prompt") or asset.get("alt") or asset["id"].replace("-", " ")
            if style and not asset.get("style"):
                asset["style"] = style
            drawn += 1
            converted_drawings.append(asset["id"])
        else:
            skipped.append(asset["id"])
    if not converted_photos and not converted_drawings and not skipped:
        return []
    _write_json(work / FRONTEND_FILE, spec)
    notes = []
    if converted_photos:
        message = f"Real photos drafted from their alt text instead of placeholders: {', '.join(converted_photos)}"
        notes.append({"spec": "frontend", "path": "/assets", "message": message, "suggestion": None})
    if converted_drawings:
        message = f"Drawn from their alt text instead of placeholders: {', '.join(converted_drawings)}"
        notes.append({"spec": "frontend", "path": "/assets", "message": message, "suggestion": None})
    if skipped:
        message = (
            f"Left as placeholders (at most {max_photos} photos, {MAX_GENERATED_ASSETS} drawings per site): "
            f"{', '.join(skipped)}; upload an image for them"
        )
        notes.append({"spec": "frontend", "path": "/assets", "message": message, "suggestion": None})
    return notes


def autofix_draft(work: Path) -> list[dict[str, Any]]:
    """Applies deterministic spec fixes (Story 18.3) to FRONTEND_FILE before validation; returns assumption notes."""
    spec, issue = _load(work / FRONTEND_FILE)
    if issue is not None or not isinstance(spec, dict) or not isinstance(spec.get("pages"), list):
        return []
    fixed_spec, notes = autofix_frontend_spec(spec)
    if notes:
        _write_json(work / FRONTEND_FILE, fixed_spec)
    return notes


def apply_manage_area(work: Path) -> list[dict[str, Any]]:
    """Adds a deterministic Manage area for uncovered operations (Story 19.7); returns assumption notes."""
    frontend_raw, issue_fe = _load(work / FRONTEND_FILE)
    backend_raw, issue_be = _load(work / BACKEND_FILE)
    if issue_fe or issue_be or not isinstance(frontend_raw, dict) or not isinstance(backend_raw, dict):
        return []
    val = validate_spec_data(backend_raw)
    if not val.report.valid or val.normalized is None:
        return []
    contract = build_contract(val.normalized)
    managed_spec, notes = add_manage_area(frontend_raw, contract)
    _write_json(work / FRONTEND_FILE, managed_spec)
    return [{"spec": "frontend", "path": "/manage", "message": note, "suggestion": None} for note in notes]


# -- usage ---------------------------------------------------------------------------------------------------------


def usage_record(result: EngineResult, prompt: RenderedPrompt) -> dict[str, Any]:
    usage = result.usage
    return {
        "purpose": result.purpose,
        "engine": result.engine,
        "prompt": f"{prompt.ref.id}@{prompt.ref.version}",
        "promptSha256": prompt.ref.sha256,
        "status": str(result.status),
        "durationMs": result.duration_ms,
        "turns": result.turns,
        "model": (usage.model if usage else None) or next((c.model for c in result.model_calls if c.model), None),
        "inputTokens": (usage.input_tokens if usage else None) or 0,
        "outputTokens": (usage.output_tokens if usage else None) or 0,
        "cacheReadTokens": (usage.cache_read_tokens if usage else None) or 0,
        "cacheWriteTokens": (usage.cache_write_tokens if usage else None) or 0,
        "costUsd": usage.cost_usd if usage else None,
        "costSource": usage.cost_source if usage else None,
        "modelCalls": len(result.model_calls),
    }


def usage_summary(calls: list[dict[str, Any]]) -> dict[str, Any]:
    priced = [call["costUsd"] for call in calls if call["costUsd"] is not None]
    return {
        "calls": calls,
        "engineMs": sum(call["durationMs"] or 0 for call in calls),
        "modelCalls": sum(call["modelCalls"] for call in calls),
        "inputTokens": sum(call["inputTokens"] for call in calls),
        "outputTokens": sum(call["outputTokens"] for call in calls),
        "costUsd": round(sum(priced), 6),
        "unpriced": len(calls) - len(priced),
    }


# -- runner --------------------------------------------------------------------------------------------------------


class DraftCancelled(Exception):
    """Raised when a draft is cancelled while running."""


class DraftRunner:
    def __init__(
        self,
        registry: EngineRegistry,
        prompts: PromptLibrary,
        store: JobStore,
        workspace_root: Path,
        worker_id: str,
        examples_dir: Path | None = None,
        heartbeat_s: float | None = None,
        queue: Any | None = None,
        events: Any | None = None,
        redis: Any | None = None,
    ):
        self.registry = registry
        self.prompts = prompts
        self.store = store
        self.root = workspace_root / "drafts"
        self.worker_id = worker_id
        self.examples_dir = examples_dir or Path(config.examples_dir)
        self.heartbeat_s = heartbeat_s if heartbeat_s is not None else config.worker_heartbeat_seconds
        self.queue = queue
        self.events = events
        self.redis = redis

    async def _is_cancelled(self, draft: SpecDraftEntity) -> bool:
        if self.redis is not None:
            try:
                flag = await self.redis.get(f"bga:cancel:draft:{draft.id}")
                if flag:
                    return True
            except Exception:
                pass
        curr_draft = self.store.draft(draft.id)
        if curr_draft is not None and curr_draft.status == SpecDraftStatus.CANCELLED:
            return True
        if draft.generation_id:
            gen = self.store.generation(draft.generation_id)
            if gen is not None and (gen.status == GenerationStatus.CANCELLED or gen.cancel_requested):
                return True
        return False

    async def _chain_generation(self, draft: SpecDraftEntity, errors: list[dict[str, Any]] | None = None) -> None:
        if not draft.generation_id:
            return
        latest = self.store.draft(draft.id)
        if latest is None:
            return
        if latest.status == SpecDraftStatus.SUCCEEDED:
            self.store.attach_draft_specs(draft.generation_id, latest)
            self.store.update_generation(draft.generation_id, status=GenerationStatus.PENDING)
            if self.events is not None:
                await self.events.publish(
                    draft.generation_id,
                    "status.changed",
                    status=GenerationStatus.PENDING,
                    payload={"engine": latest.engine, "mode": latest.mode, "lanes": initial_lanes(latest.mode)},
                )
            if self.queue is not None:
                await self.queue.enqueue(draft.generation_id, latest.engine)
        elif latest.status == SpecDraftStatus.NEEDS_REVIEW:
            self.store.update_generation(draft.generation_id, status=GenerationStatus.NEEDS_REVIEW)
            if self.events is not None:
                await self.events.publish(
                    draft.generation_id,
                    "status.changed",
                    status=GenerationStatus.NEEDS_REVIEW,
                    payload={"errors": errors or (latest.validation or {}).get("errors", [])},
                )

    async def run(self, draft_id: str) -> None:
        try:
            draft = self.store.claim_draft(uuid.UUID(draft_id), self.worker_id)
        except ValueError:
            logger.warning("ignoring a malformed draft id", extra={"draft_id": draft_id})
            return
        if draft is None:
            return  # finished, or taken by another worker
        if await self._is_cancelled(draft):
            return
        heartbeat = asyncio.create_task(self._heartbeat(draft.id))
        directory = self.root / str(draft.id)
        try:
            await self._run(draft, directory)
            if not await self._is_cancelled(draft):
                await self._chain_generation(draft)
        except DraftCancelled:
            self.store.update_draft(
                draft.id,
                status=SpecDraftStatus.CANCELLED,
                error="Cancelled",
                progress=None,
                finished_at=datetime.now(UTC),
            )
            if draft.generation_id:
                self.store.update_generation(
                    draft.generation_id,
                    status=GenerationStatus.CANCELLED,
                    finished_at=datetime.now(UTC),
                )
        except asyncio.CancelledError:
            raise  # shutdown: the reaper fails the draft once its heartbeat stops
        except Exception as exc:
            message = str(exc) if isinstance(exc, DraftFailed) else f"{type(exc).__name__}: {exc}"
            if not isinstance(exc, DraftFailed):
                logger.exception("draft failed", extra={"draft_id": str(draft.id)})
            self.store.update_draft(
                draft.id,
                status=SpecDraftStatus.FAILED,
                error=message[:2000],
                progress=None,
                finished_at=datetime.now(UTC),
            )
            if draft.generation_id:
                self.store.update_generation(
                    draft.generation_id,
                    status=GenerationStatus.FAILED,
                    error_summary=f"DRAFT_FAILED: {message}",
                    finished_at=datetime.now(UTC),
                )
                if self.events is not None:
                    await self.events.publish(
                        draft.generation_id,
                        "status.changed",
                        status=GenerationStatus.FAILED,
                        payload={"code": "DRAFT_FAILED", "error": message},
                    )
        finally:
            heartbeat.cancel()
            shutil.rmtree(directory, ignore_errors=True)

    async def _heartbeat(self, draft_id: uuid.UUID) -> None:
        while True:
            await asyncio.sleep(self.heartbeat_s)
            try:
                self.store.update_draft(draft_id)  # bumps updated_at
            except Exception as exc:
                logger.warning("draft heartbeat failed", extra={"draft_id": str(draft_id), "error": str(exc)})

    async def _run(self, draft: SpecDraftEntity, directory: Path) -> None:
        try:
            engine = self.registry.get(draft.engine)
        except LookupError as exc:
            raise DraftFailed(str(exc)) from exc
        mode = GenerationMode(draft.mode)
        shutil.rmtree(directory, ignore_errors=True)
        work, state = directory / "work", directory / "state"
        work.mkdir(parents=True)
        state.mkdir(parents=True)
        found = draft_directions(draft)
        context = write_inputs(work, draft, self.examples_dir, found)
        frontend = mode != GenerationMode.BACKEND
        purpose, version = ("draft_frontend_spec", "v7") if frontend else ("draft_spec", "v3")
        max_repairs = config.draft_repair_attempts_frontend if frontend else config.draft_repair_attempts_backend
        calls: list[dict[str, Any]] = []
        trace = tracing.GenerationTrace.open(
            str(draft.id),
            trace_id=None,
            parent=None,
            inputs={"mode": str(mode), "source": str(draft.source), "engine": engine.name},
            metadata={"draft_id": str(draft.id), "engine": engine.name, "mode": str(mode)},
            tags=["spec-draft", f"mode:{mode}", f"engine:{engine.name}"],
            name="spec-draft",
        )

        async def update_progress(prog: str, attempts_count: int | None = None) -> None:
            fields: dict[str, Any] = {"progress": prog}
            if attempts_count is not None:
                fields["attempts"] = attempts_count
            self.store.update_draft(draft.id, **fields)
            if draft.generation_id and self.events is not None:
                await self.events.publish(
                    draft.generation_id,
                    "draft.progress",
                    payload={"progress": prog, "attempts": attempts_count or 0},
                )

        async def call(step: str, prompt: RenderedPrompt) -> EngineResult:
            if await self._is_cancelled(draft):
                raise DraftCancelled("Draft cancelled")
            await engine.prepare_workspace(work, EngineContext(conventions=self.prompts.draft_conventions()))
            span = trace.root.child(
                f"engine:{engine.name}",
                "tool",
                inputs={"purpose": prompt.ref.id, "prompt": f"{prompt.ref.id}@{prompt.ref.version}"},
                metadata={"engine": engine.name, "purpose": prompt.ref.id},
            )
            request = EngineRequest(
                purpose=prompt.ref.id, workdir=work, state_dir=state, prompt=prompt.text, prompt_ref=prompt.ref
            )
            try:
                result = await engine.run(request)
            except BaseException as exc:
                span.end(error=f"{type(exc).__name__}: {exc}"[:500])
                raise
            if await self._is_cancelled(draft):
                raise DraftCancelled("Draft cancelled")
            record = usage_record(result, prompt)
            calls.append(record)
            span.end(
                outputs={"step": step, **record},
                error=None if result.ok else f"{result.status}: {result.error_message or result.error_reason}",
            )
            self.store.update_draft(draft.id, usage=usage_summary(calls))
            return result

        error: str | None = None
        try:
            await update_progress("drafting")
            result = await call("draft", self.prompts.render(purpose, version, **context))
            if result.status != EngineStatus.OK:
                raise DraftFailed(f"The {engine.name} engine stopped: {result.error_message or result.status}")
            design = apply_design(work, found) if found else None
            chosen = design["directions"][design["selected"]] if design else None
            image_notes = draw_images(work, chosen) if frontend else []
            autofix_notes = autofix_draft(work) if frontend else []
            manage_notes = apply_manage_area(work) if mode == GenerationMode.DYNAMIC else []
            await update_progress("validating")
            check = check_draft(work, mode)
            attempts = 0
            while not check.ok and attempts < max_repairs:
                attempts += 1
                await update_progress(f"repairing ({attempts}/{max_repairs})", attempts_count=attempts)
                errors = check.repair_errors()
                files = sorted({error["file"] for error in errors})
                result = await call("repair", self.prompts.render("repair_spec", "v2", files=files, errors=errors))
                if result.status != EngineStatus.OK:
                    check = check_draft(work, mode)
                    if not check.ok:
                        error = f"Repair {attempts} stopped: {result.error_message or result.status}"
                        break
                if frontend:
                    autofix_draft(work)
                if mode == GenerationMode.DYNAMIC:
                    manage_notes = apply_manage_area(work)
                check = check_draft(work, mode)
        except BaseException as exc:
            trace.close({"status": "failed"}, error=f"{type(exc).__name__}: {exc}"[:500])
            raise
        if check.backend_spec is None and check.frontend_spec is None:
            trace.close({"status": "failed"}, error="no spec written")
            raise DraftFailed(error or "The engine wrote no spec")
        photo_notes: list[dict[str, Any]] = []
        if check.ok and frontend and photos_enabled():
            if await self._is_cancelled(draft):
                raise DraftCancelled("Draft cancelled")
            spec, issue = _load(work / FRONTEND_FILE)
            if issue is None and isinstance(spec, dict) and isinstance(spec.get("assets"), list):
                photo_assets = [a for a in spec["assets"] if isinstance(a, dict) and a.get("source") == "photo"]
                if photo_assets:
                    await update_progress("photos")
                    semaphore = asyncio.Semaphore(config.image_concurrency)
                    generator = get_image_generator()

                    async def make_photo(
                        asset: dict[str, Any],
                    ) -> tuple[dict[str, Any], bool, ImageCallEntity, str | None]:
                        target_path = work / f"photo_{asset['id']}.webp"
                        success, record, reason = await generate_single_photo(
                            asset,
                            target_path,
                            generator=generator,
                            draft_id=draft.id,
                            semaphore=semaphore,
                        )
                        return asset, success, record, reason

                    results = await asyncio.gather(*(make_photo(a) for a in photo_assets))
                    records = []
                    for asset, success, record, reason in results:
                        records.append(record)
                        if success:
                            webp_file = work / f"photo_{asset['id']}.webp"
                            webp_bytes = webp_file.read_bytes()
                            sha256 = hashlib.sha256(webp_bytes).hexdigest()
                            existing = self.store.upload_by_sha256(draft.owner_id, sha256)
                            if existing is not None:
                                upload_id = existing.id
                            else:
                                with Image.open(io.BytesIO(webp_bytes)) as im:
                                    width, height = im.size
                                upload = UploadEntity(
                                    id=new_upload_id(),
                                    owner_id=draft.owner_id,
                                    filename=f"{asset['id']}.webp",
                                    mime="image/webp",
                                    bytes=len(webp_bytes),
                                    width=width,
                                    height=height,
                                    sha256=sha256,
                                    origin="photo",
                                    prompt=asset.get("prompt"),
                                )
                                target_file = Path(uploads_dir()) / upload.relative_path
                                target_file.parent.mkdir(parents=True, exist_ok=True)
                                target_file.write_bytes(webp_bytes)
                                self.store.create_upload(upload)
                                upload_id = upload.id
                            asset["source"] = f"upload:{upload_id}"
                        else:
                            msg = (
                                f"Photo for '{asset['id']}' could not be generated "
                                f"({reason or 'failed'}); generation will retry"
                            )
                            photo_notes.append(
                                {
                                    "spec": "frontend",
                                    "path": f"/assets/{asset['id']}",
                                    "message": msg,
                                    "suggestion": None,
                                }
                            )
                    self.store.add_image_calls(records)
                    _write_json(work / FRONTEND_FILE, spec)
                    check = check_draft(work, mode)
        assumptions, unresolved = read_notes(work, mode)
        if design is not None:
            assumptions += design_notes(design["directions"][design["selected"]])
        assumptions += image_notes
        assumptions += autofix_notes
        assumptions += manage_notes
        assumptions += photo_notes
        status = SpecDraftStatus.SUCCEEDED if check.ok else SpecDraftStatus.NEEDS_REVIEW
        usage = usage_summary(calls)
        image_calls_records = self.store.draft_image_calls(draft.id)
        if image_calls_records:
            img_count = len(image_calls_records)
            img_cached = sum(1 for c in image_calls_records if c.status == "cached")
            img_cost = round(sum(c.cost_usd for c in image_calls_records if c.cost_usd is not None), 6)
            usage["images"] = {"count": img_count, "cached": img_cached, "costUsd": img_cost}
            if img_cost > 0:
                usage["costUsd"] = round((usage.get("costUsd") or 0.0) + img_cost, 6)
        self.store.update_draft(
            draft.id,
            status=status,
            progress=None,
            backend_spec=check.backend_spec,
            frontend_spec=check.frontend_spec,
            assumptions=assumptions,
            unresolved=unresolved,
            design=design,
            validation=check.validation(),
            usage=usage,
            error=error,
            finished_at=datetime.now(UTC),
        )
        trace.close({"status": str(status), "repairs": len(calls) - 1})
        await tracing.GenerationTrace.flush()
