import json
import uuid
from typing import Any

from src.libs.exceptions import ErrorCode, UnprocessableEntityException
from src.modules.generations.ports.output import IGenerationRepository
from src.modules.shared.domain.backend_spec import validate_spec_data
from src.modules.shared.domain.entities import BackendSpecEntity, FrontendSpecEntity, GenerationEntity, SpecDraftEntity
from src.modules.shared.domain.enums import GenerationMode, SpecSource
from src.modules.shared.domain.frontend_spec import validate_frontend_spec_data
from src.modules.specs.ports.output import IBackendSpecRepository, IFrontendSpecRepository
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
) -> tuple[BackendSpecEntity | None, FrontendSpecEntity | None]:
    mode = GenerationMode(draft.mode)
    backend_data = backend_spec_data if backend_spec_data is not None else draft.backend_spec
    frontend_data = frontend_spec_data if frontend_spec_data is not None else draft.frontend_spec
    origin = origin_from_draft(draft)

    backend_entity: BackendSpecEntity | None = None
    if mode in NEEDS_BACKEND and backend_data is not None:
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

    frontend_entity: FrontendSpecEntity | None = None
    if mode in NEEDS_FRONTEND and frontend_data is not None:
        from src.modules.shared.domain.frontend_spec.autofix import autofix_frontend_spec
        from src.orchestrator.checks.consistency import reconcile_spec_pair

        frontend_data, _ = autofix_frontend_spec(frontend_data)
        if backend_data is not None:
            frontend_data, _ = reconcile_spec_pair(frontend_data, backend_data)
        check_uploads(draft.owner_id, frontend_data, upload_repo, is_admin=is_admin)
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

    return backend_entity, frontend_entity


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
) -> GenerationEntity:
    backend_entity, frontend_entity = create_specs_from_draft(
        draft,
        spec_repo,
        frontend_spec_repo,
        upload_repo,
        backend_spec_data=backend_spec_data,
        frontend_spec_data=frontend_spec_data,
        is_admin=is_admin,
    )
    return generation_repo.update(
        generation_id,
        spec_id=backend_entity.id if backend_entity else None,
        frontend_spec_id=frontend_entity.id if frontend_entity else None,
    )
