from typing import Annotated

from fastapi import Depends

from src.modules.health.presenter.dtos import HealthCheckResponseDto


class HealthCheckUsecase:
    async def execute(self) -> HealthCheckResponseDto:
        return HealthCheckResponseDto(status="healthy")


HealthCheckUsecaseDep = Annotated[HealthCheckUsecase, Depends(HealthCheckUsecase)]
