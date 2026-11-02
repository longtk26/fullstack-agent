import copy
import json
import uuid
from typing import Any

from src.libs.exceptions import ErrorCode, UnprocessableEntityException
from src.modules.generations.ports.output import IGenerationRepository
from src.modules.shared.domain.backend_spec import Severity, SpecIssue, validate_spec_data
from src.modules.shared.domain.entities import BackendSpecEntity, FrontendSpecEntity, GenerationEntity, SpecDraftEntity
from src.modules.shared.domain.enums import GenerationMode, SpecSource
from src.modules.shared.domain.frontend_spec import validate_frontend_spec_data
from src.modules.specs.ports.output import IBackendSpecRepository, IFrontendSpecRepository, ISpecDraftRepository
from src.modules.uploads.ports.output import IUploadRepository

NEEDS_BACKEND = {GenerationMode.BACKEND, GenerationMode.DYNAMIC}
NEEDS_FRONTEND = {GenerationMode.STATIC, GenerationMode.DYNAMIC}


def check_uploads(
    owner_id: uuid.UUID,
    frontend_spec: Any,
    upload_repo: IUploadRepository,
    is_admin: bool = False,
) -> None:
    """Story 15.4: every `upload:<id>` asset is one of the user's uploads (FE_UNKNOWN_UPLOAD)."""
    assets = frontend_spec.get("assets") if isinstance(frontend_spec, dict) else None
    issues = []
    for index, asset in enumerate(assets if isinstance(assets, list) else []):
        source = asset.get("source") if isinstance(asset, dict) else None
        if not isinstance(source, str) or not source.startswith("upload:"):
            continue
        upload = upload_repo.find(source.removeprefix("upload:"))
        if upload is None or (upload.owner_id != owner_id and not is_admin):
            issues.append(
                {
                    "code": "FE_UNKNOWN_UPLOAD",
                    "path": f"/assets/{index}/source",
                    "message": f"'{source}' is not one of your uploads",
                    "severity": "error",
                }
            )
    if issues:
        raise UnprocessableEntityException(
            "The FrontendSpec uses uploads that do not exist", code=ErrorCode.SPEC_INVALID, details=issues
        )


def prepare_frontend_spec(
    frontend_data: dict[str, Any], backend_data: dict[str, Any] | None
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Story 18.3 autofix, then (with a BackendSpec) the pair reconcile, on a copy; returns (spec, notes)."""
    from src.modules.shared.domain.frontend_spec.autofix import autofix_frontend_spec
    from src.orchestrator.checks.consistency import reconcile_spec_pair

    frontend_data, notes = autofix_frontend_spec(copy.deepcopy(frontend_data))
    if backend_data is not None:
        # The contract is built from the normalized BackendSpec (a raw one may not build at all).
        normalized = validate_spec_data(backend_data).normalized or backend_data
        frontend_data, reconcile_notes = reconcile_spec_pair(frontend_data, normalized)
        notes = [*notes, *reconcile_notes]
    return frontend_data, notes


def add_assumptions(
    draft_repo: ISpecDraftRepository | None, draft: SpecDraftEntity, notes: list[dict[str, Any]]
) -> SpecDraftEntity:
    """Keeps the automatic spec changes on the draft (its assumptions), so the user sees them."""
    known = {(n.get("path"), n.get("message")) for n in draft.assumptions if isinstance(n, dict)}
    new = [n for n in notes if (n.get("path"), n.get("message")) not in known]
    if draft_repo is None or not new:
        return draft
    return draft_repo.update(draft.id, assumptions=[*draft.assumptions, *new])


def _issue(issue: SpecIssue, spec: str) -> dict[str, Any]:
    data = issue.model_dump(mode="json", exclude_none=True)
    if "backend_path" in data:
        data["backendPath"] = data.pop("backend_path")
    return {"spec": spec, **data}


def input_issues(
    mode: GenerationMode, backend_data: dict[str, Any] | None, frontend_data: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """The errors the first node (`validate_spec` / `validate_inputs`) would fail the generation with."""
    from src.orchestrator.checks.consistency import check_spec_pair, reconcile_spec_pair

    errors: list[dict[str, Any]] = []
    backend = validate_spec_data(backend_data) if mode in NEEDS_BACKEND and backend_data is not None else None
    if backend is not None:
        errors += [_issue(issue, "backend") for issue in backend.report.errors]
    frontend = validate_frontend_spec_data(frontend_data) if mode in NEEDS_FRONTEND and frontend_data else None
    if frontend is not None:
        errors += [_issue(issue, "frontend") for issue in frontend.report.errors]
        spec_mode = frontend.normalized["project"]["mode"] if frontend.normalized else None
        if spec_mode is not None and spec_mode != mode:
            errors.append(
                {
                    "spec": "frontend",
                    "code": "MODE_INPUT_MISMATCH",
                    "path": "/project/mode",
                    "message": f"The FrontendSpec is for a '{spec_mode}' site, the generation is '{mode}'",
                }
            )
    if mode == GenerationMode.DYNAMIC and frontend and backend and frontend.normalized and backend.normalized:
        healed, _ = reconcile_spec_pair(frontend.normalized, backend.normalized)
        errors += [
            _issue(issue, "consistency")
            for issue in check_spec_pair(healed, backend.normalized)
            if issue.severity != Severity.WARNING
        ]
    return errors


def origin_from_draft(draft: SpecDraftEntity | None) -> dict[str, Any]:
    if draft is None or draft.source != SpecSource.REQUIREMENT:
        return {"source": SpecSource.JSON}
    return {"source": SpecSource.REQUIREMENT, "requirement_text": draft.requirement_text}


def create_specs_from_draft(
    draft: SpecDraftEntity,
    spec_repo: IBackendSpecRepository,
    frontend_spec_repo: IFrontendSpecRepository,
    upload_repo: IUploadRepository,
    backend_spec_data: dict[str, Any] | None = None,
    frontend_spec_data: dict[str, Any] | None = None,
    is_admin: bool = False,
    backend_entity: BackendSpecEntity | None = None,
    frontend_entity: FrontendSpecEntity | None = None,
    draft_repo: ISpecDraftRepository | None = None,
) -> tuple[BackendSpecEntity | None, FrontendSpecEntity | None]:
    """The generation's specs: the given entities (`specId` / `frontendSpecId`), else new ones from the inline
    data or the draft. A spec the mode needs and nobody provides is a 422. Notes of the automatic FrontendSpec
    fixes go to the draft's assumptions (with `draft_repo`)."""
    mode = GenerationMode(draft.mode)
    backend_data = backend_spec_data if backend_spec_data is not None else draft.backend_spec
    frontend_data = frontend_spec_data if frontend_spec_data is not None else draft.frontend_spec
    if backend_entity is not None:
        backend_data = backend_entity.normalized_json or json.loads(backend_entity.raw_json)
    if mode in NEEDS_BACKEND and backend_data is None:
        raise UnprocessableEntityException("BackendSpec is required", code=ErrorCode.MODE_INPUT_MISMATCH)
    if mode in NEEDS_FRONTEND and frontend_entity is None and frontend_data is None:
        raise UnprocessableEntityException("FrontendSpec is required", code=ErrorCode.MODE_INPUT_MISMATCH)
    origin = origin_from_draft(draft)

    if mode in NEEDS_BACKEND and backend_entity is None:
        result = validate_spec_data(backend_data)
        version = backend_data.get("specVersion")
        backend_entity = spec_repo.create(
            BackendSpecEntity(
                owner_id=draft.owner_id,
                spec_version=version if isinstance(version, str) else "unknown",
                raw_json=json.dumps(backend_data, ensure_ascii=False, indent=2),
                normalized_json=result.normalized,
                **origin,
            )
        )

    if mode in NEEDS_FRONTEND and frontend_entity is None:
        frontend_data, notes = prepare_frontend_spec(frontend_data, backend_data if mode in NEEDS_BACKEND else None)
        check_uploads(draft.owner_id, frontend_data, upload_repo, is_admin=is_admin)
        add_assumptions(draft_repo, draft, notes)
        result = validate_frontend_spec_data(frontend_data)
        version = frontend_data.get("specVersion")
        frontend_entity = frontend_spec_repo.create(
            FrontendSpecEntity(
                owner_id=draft.owner_id,
                spec_version=version if isinstance(version, str) else "unknown",
                mode=result.normalized["project"]["mode"] if result.normalized else None,
                raw_json=json.dumps(frontend_data, ensure_ascii=False, indent=2),
                normalized_json=result.normalized,
                **origin,
            )
        )

    return (
        backend_entity if mode in NEEDS_BACKEND else None,
        frontend_entity if mode in NEEDS_FRONTEND else None,
    )


def attach_draft_specs(
    generation_id: str,
    draft: SpecDraftEntity,
    generation_repo: IGenerationRepository,
    spec_repo: IBackendSpecRepository,
    frontend_spec_repo: IFrontendSpecRepository,
    upload_repo: IUploadRepository,
    backend_spec_data: dict[str, Any] | None = None,
    frontend_spec_data: dict[str, Any] | None = None,
    is_admin: bool = False,
    backend_entity: BackendSpecEntity | None = None,
    frontend_entity: FrontendSpecEntity | None = None,
    draft_repo: ISpecDraftRepository | None = None,
) -> GenerationEntity:
    backend_entity, frontend_entity = create_specs_from_draft(
        draft,
        spec_repo,
        frontend_spec_repo,
        upload_repo,
        backend_spec_data=backend_spec_data,
        frontend_spec_data=frontend_spec_data,
        is_admin=is_admin,
        backend_entity=backend_entity,
        frontend_entity=frontend_entity,
        draft_repo=draft_repo,
    )
    return generation_repo.update(
        generation_id,
        spec_id=backend_entity.id if backend_entity else None,
        frontend_spec_id=frontend_entity.id if frontend_entity else None,
    )
