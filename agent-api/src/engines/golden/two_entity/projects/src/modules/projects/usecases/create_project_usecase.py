from typing import Annotated

from fastapi import Depends

from src.configs import get_logger
from src.libs.decorators.transactional_decorator import Transactional
from src.modules.projects.ports.output import IProjectRepoDep
from src.modules.projects.presenter.dtos import CreateProjectRequestDto, ProjectResponseDto

logger = get_logger(__name__)


class CreateProjectUsecase:
    def __init__(self, project_repo: IProjectRepoDep):
        self.project_repo = project_repo

    @Transactional
    async def execute(self, dto: CreateProjectRequestDto) -> ProjectResponseDto:
        project = self.project_repo.create(dto.to_entity())
        logger.info("project created", extra={"project_id": str(project.id)})
        return ProjectResponseDto.from_entity(project)


CreateProjectUsecaseDep = Annotated[CreateProjectUsecase, Depends(CreateProjectUsecase)]
