import uuid
from typing import Annotated

from fastapi import Depends

from src.libs.exceptions import NotFoundException
from src.modules.projects.ports.output import IProjectRepoDep
from src.modules.projects.presenter.dtos import ProjectResponseDto


class GetProjectUsecase:
    def __init__(self, project_repo: IProjectRepoDep):
        self.project_repo = project_repo

    async def execute(self, project_id: uuid.UUID) -> ProjectResponseDto:
        project = self.project_repo.find_by_id(project_id)
        if project is None:
            raise NotFoundException("Project not found", details={"id": str(project_id)})
        return ProjectResponseDto.from_entity(project)


GetProjectUsecaseDep = Annotated[GetProjectUsecase, Depends(GetProjectUsecase)]
