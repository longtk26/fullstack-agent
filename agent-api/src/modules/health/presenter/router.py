from fastapi import APIRouter

from src.modules.health.presenter.dtos import HealthCheckResponseDto
from src.modules.health.usecases import HealthCheckUsecaseDep

health_router = APIRouter(tags=["health"])


@health_router.get("/health", response_model=HealthCheckResponseDto)
async def health_check(usecase: HealthCheckUsecaseDep):
    return await usecase.execute()
