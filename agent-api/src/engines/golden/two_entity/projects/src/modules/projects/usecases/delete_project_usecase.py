import uuid
from typing import Annotated

from fastapi import Depends

from src.configs import get_logger
from src.libs.decorators.transactional_decorator import Transactional
from src.libs.exceptions import NotFoundException
from src.modules.projects.ports.output import IProjectRepoDep

logger = get_logger(__name__)


class DeleteProjectUsecase:
    def __init__(self, project_repo: IProjectRepoDep):
        self.project_repo = project_repo

    @Transactional
    async def execute(self, project_id: uuid.UUID) -> None:
        if self.project_repo.find_by_id(project_id) is None:
            raise NotFoundException("Project not found", details={"id": str(project_id)})
        self.project_repo.delete(project_id)
        logger.info("project deleted", extra={"project_id": str(project_id)})


DeleteProjectUsecaseDep = Annotated[DeleteProjectUsecase, Depends(DeleteProjectUsecase)]
