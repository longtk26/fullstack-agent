import uuid
from typing import Annotated

from fastapi import Depends

from src.configs import get_logger
from src.libs.decorators.transactional_decorator import Transactional
from src.libs.exceptions import NotFoundException
from src.modules.tasks.ports.output import ITaskRepoDep
from src.modules.tasks.presenter.dtos import TaskResponseDto, UpdateTaskRequestDto

logger = get_logger(__name__)


class UpdateTaskUsecase:
    def __init__(self, task_repo: ITaskRepoDep):
        self.task_repo = task_repo

    @Transactional
    async def execute(self, task_id: uuid.UUID, dto: UpdateTaskRequestDto) -> TaskResponseDto:
        current = self.task_repo.find_by_id(task_id)
        if current is None:
            raise NotFoundException("Task not found", details={"id": str(task_id)})
        task = self.task_repo.update(dto.to_entity(current))
        logger.info("task updated", extra={"task_id": str(task_id)})
        return TaskResponseDto.from_entity(task)


UpdateTaskUsecaseDep = Annotated[UpdateTaskUsecase, Depends(UpdateTaskUsecase)]
