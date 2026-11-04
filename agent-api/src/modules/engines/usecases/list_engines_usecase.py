from datetime import datetime
from typing import Annotated

from fastapi import Depends
from pydantic import BaseModel

from src.engines import EngineHealth
from src.modules.engines.infrastructure.adapters import EngineHealthStoreDep, EngineRegistryDep


class EngineCatalog(BaseModel):
    default: str
    draft_default: str  # Story 18.10: the engine that drafts specs unless the user picks another
    engines: list[EngineHealth]
    reported_by_worker: bool
    reported_at: datetime | None = None


class ListEnginesUsecase:
    def __init__(self, registry: EngineRegistryDep, store: EngineHealthStoreDep):
        self.registry = registry
        self.store = store

    async def execute(self) -> EngineCatalog:
        report = await self.store.read(self.registry.names())
        if report is not None:
            for health in report.engines:
                health.drafts_only = self.registry.get(health.name).drafts_only
            return EngineCatalog(
                default=self.registry.default,
                draft_default=self.registry.draft_default,
                engines=report.engines,
                reported_by_worker=True,
                reported_at=report.reported_at,
            )
        local = [
            health.model_copy(
                update={"available": False, "reason": f"Worker not reporting; checked locally: {health.reason or 'ok'}"}
            )
            if health.name != "fake"
            else health
            for health in await self.registry.health()
        ]
        return EngineCatalog(
            default=self.registry.default,
            draft_default=self.registry.draft_default,
            engines=local,
            reported_by_worker=False,
        )


ListEnginesUsecaseDep = Annotated[ListEnginesUsecase, Depends(ListEnginesUsecase)]
