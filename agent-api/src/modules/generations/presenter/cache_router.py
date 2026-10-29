from fastapi import APIRouter

from src.modules.auth.presenter import AdminUserDep
from src.modules.generations.usecases import PurgeComponentCacheUsecaseDep

cache_router = APIRouter(prefix="/api/v1/cache", tags=["cache"])


@cache_router.delete("/components")
async def purge_component_cache(_: AdminUserDep, usecase: PurgeComponentCacheUsecaseDep) -> dict[str, int]:
    """Admin only: drops every cached custom component (Story 17.3)."""
    return {"purged": await usecase.execute()}
