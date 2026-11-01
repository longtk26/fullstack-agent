import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends

from src.libs.decorators.transactional_decorator import Transactional
from src.libs.exceptions import ConflictException, ErrorCode
from src.modules.generations.infrastructure.adapters import EventPublisherDep, JobQueueDep
from src.modules.generations.infrastructure.persistence import TERMINAL
from src.modules.generations.ports.output import IGenerationRepoDep
from src.modules.generations.usecases.get_generation_usecase import GetGenerationUsecaseDep
from src.modules.shared.domain.entities import GenerationEntity, UserEntity
from src.modules.shared.domain.enums import GenerationStatus, SpecDraftStatus
from src.modules.shared.domain.generation_modes import close_lanes
from src.modules.specs.ports.output import ISpecDraftRepoDep


class CancelGenerationUsecase:
    def __init__(
        self,
        generation_repo: IGenerationRepoDep,
        getter: GetGenerationUsecaseDep,
        queue: JobQueueDep,
        events: EventPublisherDep,
        draft_repo: ISpecDraftRepoDep,
    ):
        self.generation_repo = generation_repo
        self.getter = getter
        self.queue = queue
        self.events = events
        self.draft_repo = draft_repo

    async def execute(self, generation_id: str, user: UserEntity) -> GenerationEntity:
        generation = self.getter.load(generation_id, user)
        if generation.status in TERMINAL:
            raise ConflictException(f"Generation is already {generation.status}", code=ErrorCode.ALREADY_FINISHED)
        if generation.status in (GenerationStatus.DRAFTING, GenerationStatus.NEEDS_REVIEW):
            draft_id = generation.options.get("draftId")
            if draft_id:
                await self.queue.remove_queued_draft(str(draft_id))
                await self.queue.redis.set(f"bga:cancel:draft:{draft_id}", "1", ex=3600)
                try:
                    self.draft_repo.update(uuid.UUID(draft_id), status=SpecDraftStatus.CANCELLED, error="Cancelled")
                except Exception:
                    pass
            cancelled = await self._mark(
                generation_id,
                status=GenerationStatus.CANCELLED,
                finished_at=datetime.now(UTC),
                lanes=close_lanes(generation.lanes, failed=False),
            )
            await self.events.publish(
                generation_id, "status.changed", status=GenerationStatus.CANCELLED, payload={"lanes": cancelled.lanes}
            )
            return cancelled
        if generation.status == GenerationStatus.PENDING and await self.queue.remove_queued(generation_id):
            cancelled = await self._mark(
                generation_id,
                status=GenerationStatus.CANCELLED,
                finished_at=datetime.now(UTC),
                lanes=close_lanes(generation.lanes, failed=False),
            )
            await self.events.publish(
                generation_id, "status.changed", status=GenerationStatus.CANCELLED, payload={"lanes": cancelled.lanes}
            )
            return cancelled
        # Running (or just picked up): the worker stops the engine and finishes the job as CANCELLED.
        updated = await self._mark(generation_id, cancel_requested=True)
        await self.queue.request_cancel(generation_id)
        await self.events.publish(generation_id, "cancel.requested", status=generation.status)
        return updated

    @Transactional
    async def _mark(self, generation_id: str, **fields) -> GenerationEntity:
        return self.generation_repo.update(generation_id, **fields)


CancelGenerationUsecaseDep = Annotated[CancelGenerationUsecase, Depends(CancelGenerationUsecase)]
