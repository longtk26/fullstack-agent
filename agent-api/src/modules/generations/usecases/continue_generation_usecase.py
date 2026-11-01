import uuid
from typing import Annotated, Any

from fastapi import Depends
from pydantic import BaseModel

from src.libs.decorators.transactional_decorator import Transactional
from src.libs.exceptions import ConflictException, ErrorCode, NotFoundException, UnprocessableEntityException
from src.modules.generations.domain.attach_specs import NEEDS_BACKEND, NEEDS_FRONTEND, attach_draft_specs
from src.modules.generations.infrastructure.adapters import EventPublisherDep, JobQueueDep
from src.modules.generations.ports.output import IGenerationRepoDep
from src.modules.shared.domain.entities import GenerationEntity, SpecDraftEntity, UserEntity
from src.modules.shared.domain.enums import GenerationMode, GenerationStatus, SpecDraftStatus
from src.modules.specs.ports.output import IBackendSpecRepoDep, IFrontendSpecRepoDep, ISpecDraftRepoDep
from src.modules.uploads.ports.output import IUploadRepoDep


class ContinueGenerationInputs(BaseModel):
    backend_spec: dict[str, Any] | None = None
    frontend_spec: dict[str, Any] | None = None


class ContinueGenerationUsecase:
    def __init__(
        self,
        generation_repo: IGenerationRepoDep,
        draft_repo: ISpecDraftRepoDep,
        spec_repo: IBackendSpecRepoDep,
        frontend_spec_repo: IFrontendSpecRepoDep,
        upload_repo: IUploadRepoDep,
        queue: JobQueueDep,
        events: EventPublisherDep,
    ):
        self.generation_repo = generation_repo
        self.draft_repo = draft_repo
        self.spec_repo = spec_repo
        self.frontend_spec_repo = frontend_spec_repo
        self.upload_repo = upload_repo
        self.queue = queue
        self.events = events

    async def execute(
        self,
        generation_id: str,
        user: UserEntity,
        inputs: ContinueGenerationInputs,
    ) -> GenerationEntity:
        generation = self.generation_repo.find_by_id(generation_id)
        if generation is None:
            raise NotFoundException("Generation not found", code=ErrorCode.NOT_FOUND)
        if generation.owner_id != user.id and not user.is_admin:
            raise NotFoundException("Generation not found", code=ErrorCode.NOT_FOUND)
        if generation.status != GenerationStatus.NEEDS_REVIEW:
            raise ConflictException(
                f"Generation is in status '{generation.status}', expected 'NEEDS_REVIEW'",
                code=ErrorCode.CONFLICT,
            )

        draft_id = generation.options.get("draftId")
        draft = self.draft_repo.find_by_id(uuid.UUID(draft_id)) if draft_id else None
        if draft is None:
            raise UnprocessableEntityException("Generation draft not found", code=ErrorCode.VALIDATION_ERROR)

        mode = GenerationMode(generation.mode)
        b_spec = inputs.backend_spec or draft.backend_spec
        f_spec = inputs.frontend_spec or draft.frontend_spec
        if mode in NEEDS_BACKEND and b_spec is None:
            raise UnprocessableEntityException("BackendSpec is required", code=ErrorCode.MODE_INPUT_MISMATCH)
        if mode in NEEDS_FRONTEND and f_spec is None:
            raise UnprocessableEntityException("FrontendSpec is required", code=ErrorCode.MODE_INPUT_MISMATCH)

        generation = await self._persist_continue(generation.id, draft, b_spec, f_spec, user.is_admin)

        await self.queue.enqueue(generation.id, generation.engine)
        await self.events.publish(
            generation.id,
            "status.changed",
            status=GenerationStatus.PENDING,
            payload={"engine": generation.engine, "mode": generation.mode, "lanes": generation.lanes},
        )
        return generation

    @Transactional
    async def _persist_continue(
        self,
        generation_id: str,
        draft: SpecDraftEntity,
        backend_spec: dict[str, Any] | None,
        frontend_spec: dict[str, Any] | None,
        is_admin: bool,
    ) -> GenerationEntity:
        update_fields: dict[str, Any] = {"status": SpecDraftStatus.SUCCEEDED}
        if backend_spec is not None:
            update_fields["backend_spec"] = backend_spec
        if frontend_spec is not None:
            from src.modules.shared.domain.frontend_spec.autofix import autofix_frontend_spec
            from src.orchestrator.checks.consistency import reconcile_spec_pair

            frontend_spec, _ = autofix_frontend_spec(frontend_spec)
            if backend_spec is not None:
                frontend_spec, _ = reconcile_spec_pair(frontend_spec, backend_spec)
            update_fields["frontend_spec"] = frontend_spec
        draft = self.draft_repo.update(draft.id, **update_fields)

        attach_draft_specs(
            generation_id,
            draft,
            self.generation_repo,
            self.spec_repo,
            self.frontend_spec_repo,
            self.upload_repo,
            backend_spec_data=backend_spec,
            frontend_spec_data=frontend_spec,
            is_admin=is_admin,
        )
        return self.generation_repo.update(generation_id, status=GenerationStatus.PENDING)


ContinueGenerationUsecaseDep = Annotated[ContinueGenerationUsecase, Depends(ContinueGenerationUsecase)]
