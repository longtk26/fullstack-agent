import json
from typing import Annotated, Any

from fastapi import Depends
from pydantic import BaseModel

from src.configs import config
from src.libs.decorators.transactional_decorator import Transactional
from src.libs.exceptions import ErrorCode, PayloadTooLargeException, UnprocessableEntityException
from src.modules.generations.infrastructure.adapters import EngineRegistryDep, JobQueueDep
from src.modules.shared.domain.entities import SpecDraftEntity, UserEntity
from src.modules.shared.domain.enums import GenerationMode, SpecSource
from src.modules.shared.domain.requirement import RequirementError, RequirementFormat, check_requirement
from src.modules.specs.ports.output import ISpecDraftRepoDep


class DraftRequest(BaseModel):
    source: SpecSource = SpecSource.REQUIREMENT
    mode: GenerationMode = GenerationMode.BACKEND
    requirement_text: str | None = None
    requirement_format: RequirementFormat | None = None
    requirement_file_name: str | None = None
    base_spec: dict[str, Any] | None = None
    site_json: dict[str, Any] | None = None
    engine: str | None = None


class CreateSpecDraftUsecase:
    """Stories 2.4, 12.4: stores a draft job and queues it for the worker; the engine never runs in the request."""

    def __init__(self, drafts: ISpecDraftRepoDep, queue: JobQueueDep, registry: EngineRegistryDep):
        self.drafts = drafts
        self.queue = queue
        self.registry = registry

    async def execute(self, user: UserEntity, request: DraftRequest) -> SpecDraftEntity:
        engine = request.engine or self.registry.default
        if engine not in self.registry.names():
            raise UnprocessableEntityException(f"Engine '{engine}' is not enabled", code=ErrorCode.ENGINE_UNKNOWN)
        draft = self._persist(user, request, engine)
        # Queued after the commit, so the worker always finds the row it is handed.
        await self.queue.enqueue_draft(str(draft.id), engine)
        return draft

    @Transactional
    def _persist(self, user: UserEntity, request: DraftRequest, engine: str) -> SpecDraftEntity:
        fields: dict[str, Any] = {}
        if request.source == SpecSource.REQUIREMENT:
            try:
                requirement = check_requirement(
                    request.requirement_text,
                    config.requirement_max_bytes,
                    request.requirement_file_name,
                    request.requirement_format,
                )
            except RequirementError as exc:
                raise UnprocessableEntityException(str(exc), code=ErrorCode.REQUIREMENT_INVALID) from exc
            fields = {
                "requirement_text": requirement.text,
                "requirement_format": requirement.format,
                "requirement_file_name": requirement.file_name,
            }
        elif request.source == SpecSource.FRONTEND:
            if request.mode != GenerationMode.BACKEND:
                raise UnprocessableEntityException(
                    "Refining an imported site drafts a BackendSpec; use mode 'backend'",
                    code=ErrorCode.MODE_INPUT_MISMATCH,
                )
            if request.base_spec is None or request.site_json is None:
                raise UnprocessableEntityException(
                    "source 'frontend' takes 'baseSpec' and 'siteJson'", code=ErrorCode.MODE_INPUT_MISMATCH
                )
            inputs = {"baseSpec": request.base_spec, "siteJson": request.site_json}
            if len(json.dumps(inputs)) > config.frontend_import_max_bytes:
                raise PayloadTooLargeException(f"The draft inputs exceed {config.frontend_import_max_bytes} bytes")
            fields = {"inputs": inputs}
        else:
            raise UnprocessableEntityException("source must be 'requirement' or 'frontend'")
        return self.drafts.create(
            SpecDraftEntity(owner_id=user.id, source=request.source, mode=request.mode, engine=engine, **fields)
        )


CreateSpecDraftUsecaseDep = Annotated[CreateSpecDraftUsecase, Depends(CreateSpecDraftUsecase)]
