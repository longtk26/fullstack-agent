from fastapi import APIRouter

from src.modules.auth.presenter import CurrentUserDep
from src.modules.engines.presenter.dtos import EngineDto, ListEnginesResponseDto
from src.modules.engines.usecases import ListEnginesUsecaseDep

engine_router = APIRouter(prefix="/api/v1/engines", tags=["engines"])


@engine_router.get("", response_model=ListEnginesResponseDto)
async def list_engines(_: CurrentUserDep, usecase: ListEnginesUsecaseDep) -> ListEnginesResponseDto:
    catalog = await usecase.execute()
    return ListEnginesResponseDto(
        default=catalog.default,
        engines=[EngineDto(name=e.name, available=e.available, reason=e.reason) for e in catalog.engines],
        reported_by_worker=catalog.reported_by_worker,
        reported_at=catalog.reported_at,
    )
