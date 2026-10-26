from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from src.modules.auth.presenter import CurrentUserDep
from src.modules.previews.presenter.dtos import PreviewDto, PreviewListDto, PreviewLogsDto, PreviewRequestsDto
from src.modules.previews.usecases import (
    ListPreviewsUsecaseDep,
    PreviewAction,
    PreviewActionUsecaseDep,
    PreviewQueryUsecaseDep,
    TouchPreviewUsecaseDep,
)

preview_router = APIRouter(prefix="/api/v1/generations/{generation_id}/preview", tags=["previews"])
previews_router = APIRouter(prefix="/api/v1/previews", tags=["previews"])


@preview_router.get("", response_model=PreviewDto)
async def get_preview(generation_id: str, user: CurrentUserDep, usecase: PreviewQueryUsecaseDep) -> PreviewDto:
    return PreviewDto.from_entity(usecase.get(generation_id, user))


async def _act(generation_id: str, user, usecase, action: PreviewAction) -> PreviewDto:
    return PreviewDto.from_entity(await usecase.execute(generation_id, user, action))


@preview_router.post("/start", response_model=PreviewDto, status_code=status.HTTP_202_ACCEPTED)
async def start_preview(generation_id: str, user: CurrentUserDep, usecase: PreviewActionUsecaseDep) -> PreviewDto:
    return await _act(generation_id, user, usecase, "start")


@preview_router.post("/stop", response_model=PreviewDto, status_code=status.HTTP_202_ACCEPTED)
async def stop_preview(generation_id: str, user: CurrentUserDep, usecase: PreviewActionUsecaseDep) -> PreviewDto:
    return await _act(generation_id, user, usecase, "stop")


@preview_router.post("/restart", response_model=PreviewDto, status_code=status.HTTP_202_ACCEPTED)
async def restart_preview(generation_id: str, user: CurrentUserDep, usecase: PreviewActionUsecaseDep) -> PreviewDto:
    return await _act(generation_id, user, usecase, "restart")


@preview_router.post("/reset-db", response_model=PreviewDto, status_code=status.HTTP_202_ACCEPTED)
async def reset_preview_db(generation_id: str, user: CurrentUserDep, usecase: PreviewActionUsecaseDep) -> PreviewDto:
    return await _act(generation_id, user, usecase, "reset-db")


@preview_router.delete("", status_code=status.HTTP_202_ACCEPTED)
async def delete_preview(generation_id: str, user: CurrentUserDep, usecase: PreviewActionUsecaseDep) -> Response:
    await usecase.execute(generation_id, user, "delete")
    return Response(status_code=status.HTTP_202_ACCEPTED)


@preview_router.post("/touch", response_model=PreviewDto)
async def touch_preview(generation_id: str, user: CurrentUserDep, usecase: TouchPreviewUsecaseDep) -> PreviewDto:
    return PreviewDto.from_entity(await usecase.execute(generation_id, user))


@preview_router.get("/logs", response_model=PreviewLogsDto)
async def preview_logs(
    generation_id: str,
    user: CurrentUserDep,
    usecase: PreviewQueryUsecaseDep,
    tail: Annotated[int, Query(ge=1, le=2000)] = 200,
) -> PreviewLogsDto:
    return PreviewLogsDto.model_validate(await usecase.logs(generation_id, user, tail))


@preview_router.get("/requests", response_model=PreviewRequestsDto)
async def preview_requests(
    generation_id: str,
    user: CurrentUserDep,
    usecase: PreviewQueryUsecaseDep,
    after: Annotated[str | None, Query(max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> PreviewRequestsDto:
    return PreviewRequestsDto.from_reply(await usecase.requests(generation_id, user, after, limit))


@previews_router.get("", response_model=PreviewListDto)
async def list_previews(
    user: CurrentUserDep,
    usecase: ListPreviewsUsecaseDep,
    scope: Annotated[str, Query(pattern="^(mine|all)$")] = "mine",
) -> PreviewListDto:
    return PreviewListDto(items=[PreviewDto.from_entity(p) for p in await usecase.execute(user, scope == "all")])
