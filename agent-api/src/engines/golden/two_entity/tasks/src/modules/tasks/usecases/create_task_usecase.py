from typing import Annotated

from fastapi import Depends

from src.configs import get_logger
from src.libs.decorators.transactional_decorator import Transactional
from src.modules.tasks.ports.output import ITaskRepoDep
from src.modules.tasks.presenter.dtos import CreateTaskRequestDto, TaskResponseDto

logger = get_logger(__name__)


class CreateTaskUsecase:
    def __init__(self, task_repo: ITaskRepoDep):
        self.task_repo = task_repo

    @Transactional
    async def execute(self, dto: CreateTaskRequestDto) -> TaskResponseDto:
        task = self.task_repo.create(dto.to_entity())
        logger.info("task created", extra={"task_id": str(task.id), "project_id": str(task.project_id)})
        return TaskResponseDto.from_entity(task)


CreateTaskUsecaseDep = Annotated[CreateTaskUsecase, Depends(CreateTaskUsecase)]
