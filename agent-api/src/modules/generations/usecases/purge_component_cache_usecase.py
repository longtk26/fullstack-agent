from typing import Annotated

from fastapi import Depends

from src.libs.decorators.transactional_decorator import Transactional
from src.modules.generations.ports.output import IComponentCacheRepoDep
from src.orchestrator.component_cache import drop_files


class PurgeComponentCacheUsecase:
    """Story 17.3: empties the shared component cache (rows and files); the next generations regenerate."""

    def __init__(self, cache_repo: IComponentCacheRepoDep):
        self.cache_repo = cache_repo

    @Transactional
    async def execute(self) -> int:
        purged = self.cache_repo.purge()
        drop_files()
        return purged


PurgeComponentCacheUsecaseDep = Annotated[PurgeComponentCacheUsecase, Depends(PurgeComponentCacheUsecase)]
