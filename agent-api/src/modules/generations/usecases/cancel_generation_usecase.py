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
from src.modules.shared.domain.enums import GenerationStatus


class CancelGenerationUsecase:
    def __init__(
        self,
        generation_repo: IGenerationRepoDep,
        getter: GetGenerationUsecaseDep,
        queue: JobQueueDep,
        events: EventPublisherDep,
    ):
        self.generation_repo = generation_repo
        self.getter = getter
        self.queue = queue
        self.events = events

    async def execute(self, generation_id: str, user: UserEntity) -> GenerationEntity:
        generation = self.getter.load(generation_id, user)
        if generation.status in TERMINAL:
            raise ConflictException(f"Generation is already {generation.status}", code=ErrorCode.ALREADY_FINISHED)
        if generation.status == GenerationStatus.PENDING and await self.queue.remove_queued(generation_id):
            cancelled = await self._mark(
                generation_id, status=GenerationStatus.CANCELLED, finished_at=datetime.now(UTC)
            )
            await self.events.publish(generation_id, "status.changed", status=GenerationStatus.CANCELLED)
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
