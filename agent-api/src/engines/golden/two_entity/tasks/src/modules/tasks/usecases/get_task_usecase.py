import uuid
from typing import Annotated

from fastapi import Depends

from src.libs.exceptions import NotFoundException
from src.modules.tasks.ports.output import ITaskRepoDep
from src.modules.tasks.presenter.dtos import TaskResponseDto


class GetTaskUsecase:
    def __init__(self, task_repo: ITaskRepoDep):
        self.task_repo = task_repo

    async def execute(self, task_id: uuid.UUID) -> TaskResponseDto:
        task = self.task_repo.find_by_id(task_id)
        if task is None:
            raise NotFoundException("Task not found", details={"id": str(task_id)})
        return TaskResponseDto.from_entity(task)


GetTaskUsecaseDep = Annotated[GetTaskUsecase, Depends(GetTaskUsecase)]
