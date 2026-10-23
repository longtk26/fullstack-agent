import uuid
from typing import Annotated

from fastapi import Depends

from src.modules.shared.domain.entities import TaskStatus
from src.modules.tasks.ports.output import ITaskRepoDep
from src.modules.tasks.presenter.dtos import ListTasksResponseDto, TaskResponseDto

# API sort names (camelCase) → entity attributes
SORT_FIELDS = {"priority": "priority", "dueDate": "due_date"}


class ListTasksUsecase:
    def __init__(self, task_repo: ITaskRepoDep):
        self.task_repo = task_repo

    async def execute(
        self,
        project_id: uuid.UUID | None,
        status: TaskStatus | None,
        sort: str | None,
        limit: int,
        offset: int,
    ) -> ListTasksResponseDto:
        candidates = {"project_id": project_id, "status": status}
        filters = {key: value for key, value in candidates.items() if value is not None}
        order = (SORT_FIELDS[sort.lstrip("-")], sort.startswith("-")) if sort else None
        tasks, total = self.task_repo.list(filters, order, limit, offset)
        return ListTasksResponseDto(
            items=[TaskResponseDto.from_entity(task) for task in tasks], total=total, limit=limit, offset=offset
        )


ListTasksUsecaseDep = Annotated[ListTasksUsecase, Depends(ListTasksUsecase)]
