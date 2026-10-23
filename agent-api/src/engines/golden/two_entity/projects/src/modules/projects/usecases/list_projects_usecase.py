from typing import Annotated

from fastapi import Depends

from src.modules.projects.ports.output import IProjectRepoDep
from src.modules.projects.presenter.dtos import ListProjectsResponseDto, ProjectResponseDto

# API sort names (camelCase) → entity attributes
SORT_FIELDS = {"name": "name", "createdAt": "created_at"}


class ListProjectsUsecase:
    def __init__(self, project_repo: IProjectRepoDep):
        self.project_repo = project_repo

    async def execute(self, sort: str | None, limit: int, offset: int) -> ListProjectsResponseDto:
        order = (SORT_FIELDS[sort.lstrip("-")], sort.startswith("-")) if sort else None
        projects, total = self.project_repo.list(order, limit, offset)
        return ListProjectsResponseDto(
            items=[ProjectResponseDto.from_entity(project) for project in projects],
            total=total,
            limit=limit,
            offset=offset,
        )


ListProjectsUsecaseDep = Annotated[ListProjectsUsecase, Depends(ListProjectsUsecase)]
