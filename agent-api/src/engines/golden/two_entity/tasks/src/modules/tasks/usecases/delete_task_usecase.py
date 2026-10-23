import uuid
from typing import Annotated

from fastapi import Depends

from src.configs import get_logger
from src.libs.decorators.transactional_decorator import Transactional
from src.libs.exceptions import NotFoundException
from src.modules.tasks.ports.output import ITaskRepoDep

logger = get_logger(__name__)


class DeleteTaskUsecase:
    def __init__(self, task_repo: ITaskRepoDep):
        self.task_repo = task_repo

    @Transactional
    async def execute(self, task_id: uuid.UUID) -> None:
        if self.task_repo.find_by_id(task_id) is None:
            raise NotFoundException("Task not found", details={"id": str(task_id)})
        self.task_repo.delete(task_id)
        logger.info("task deleted", extra={"task_id": str(task_id)})


DeleteTaskUsecaseDep = Annotated[DeleteTaskUsecase, Depends(DeleteTaskUsecase)]
