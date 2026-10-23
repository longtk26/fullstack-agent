import uuid
from typing import Annotated

from fastapi import Depends

from src.configs import get_logger
from src.libs.decorators.transactional_decorator import Transactional
from src.libs.exceptions import NotFoundException
from src.modules.projects.ports.output import IProjectRepoDep
from src.modules.projects.presenter.dtos import ProjectResponseDto, UpdateProjectRequestDto

logger = get_logger(__name__)


class UpdateProjectUsecase:
    def __init__(self, project_repo: IProjectRepoDep):
        self.project_repo = project_repo

    @Transactional
    async def execute(self, project_id: uuid.UUID, dto: UpdateProjectRequestDto) -> ProjectResponseDto:
        current = self.project_repo.find_by_id(project_id)
        if current is None:
            raise NotFoundException("Project not found", details={"id": str(project_id)})
        project = self.project_repo.update(dto.to_entity(current))
        logger.info("project updated", extra={"project_id": str(project_id)})
        return ProjectResponseDto.from_entity(project)


UpdateProjectUsecaseDep = Annotated[UpdateProjectUsecase, Depends(UpdateProjectUsecase)]
