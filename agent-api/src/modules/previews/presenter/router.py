from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from src.modules.auth.presenter import CurrentUserDep
from src.modules.previews.presenter.dtos import PreviewDto, PreviewListDto, PreviewLogsDto, PreviewRequestsDto
from src.modules.previews.usecases import (
    ListPreviewsUsecaseDep,
    PreviewAction,
    PreviewActionUsecaseDep,
    PreviewKind,
    PreviewQueryUsecaseDep,
    TouchPreviewUsecaseDep,
)

preview_router = APIRouter(prefix="/api/v1/generations/{generation_id}/preview", tags=["previews"])
integration_router = APIRouter(prefix="/api/v1/generations/{generation_id}/integration", tags=["previews"])
previews_router = APIRouter(prefix="/api/v1/previews", tags=["previews"])


# `kind=frontend` addresses the frontend preview (Story 13.5); the default is the backend preview.
KindQuery = Annotated[PreviewKind, Query()]


@preview_router.get("", response_model=PreviewDto)
async def get_preview(
    generation_id: str, user: CurrentUserDep, usecase: PreviewQueryUsecaseDep, kind: KindQuery = "backend"
) -> PreviewDto:
    return PreviewDto.from_entity(usecase.get(generation_id, user, kind))


async def _act(generation_id: str, user, usecase, action: PreviewAction, kind: PreviewKind = "backend") -> PreviewDto:
    return PreviewDto.from_entity(await usecase.execute(generation_id, user, action, kind))


@preview_router.post("/start", response_model=PreviewDto, status_code=status.HTTP_202_ACCEPTED)
async def start_preview(
    generation_id: str, user: CurrentUserDep, usecase: PreviewActionUsecaseDep, kind: KindQuery = "backend"
) -> PreviewDto:
    return await _act(generation_id, user, usecase, "start", kind)


@preview_router.post("/stop", response_model=PreviewDto, status_code=status.HTTP_202_ACCEPTED)
async def stop_preview(
    generation_id: str, user: CurrentUserDep, usecase: PreviewActionUsecaseDep, kind: KindQuery = "backend"
) -> PreviewDto:
    return await _act(generation_id, user, usecase, "stop", kind)


@preview_router.post("/restart", response_model=PreviewDto, status_code=status.HTTP_202_ACCEPTED)
async def restart_preview(
    generation_id: str, user: CurrentUserDep, usecase: PreviewActionUsecaseDep, kind: KindQuery = "backend"
) -> PreviewDto:
    return await _act(generation_id, user, usecase, "restart", kind)


@preview_router.post("/reset-db", response_model=PreviewDto, status_code=status.HTTP_202_ACCEPTED)
async def reset_preview_db(generation_id: str, user: CurrentUserDep, usecase: PreviewActionUsecaseDep) -> PreviewDto:
    return await _act(generation_id, user, usecase, "reset-db")


@preview_router.delete("", status_code=status.HTTP_202_ACCEPTED)
async def delete_preview(
    generation_id: str, user: CurrentUserDep, usecase: PreviewActionUsecaseDep, kind: KindQuery = "backend"
) -> Response:
    await usecase.execute(generation_id, user, "delete", kind)
    return Response(status_code=status.HTTP_202_ACCEPTED)


@preview_router.post("/touch", response_model=PreviewDto)
async def touch_preview(
    generation_id: str, user: CurrentUserDep, usecase: TouchPreviewUsecaseDep, kind: KindQuery = "backend"
) -> PreviewDto:
    return PreviewDto.from_entity(await usecase.execute(generation_id, user, kind))


@preview_router.get("/logs", response_model=PreviewLogsDto)
async def preview_logs(
    generation_id: str,
    user: CurrentUserDep,
    usecase: PreviewQueryUsecaseDep,
    tail: Annotated[int, Query(ge=1, le=2000)] = 200,
    kind: KindQuery = "backend",
) -> PreviewLogsDto:
    return PreviewLogsDto.model_validate(await usecase.logs(generation_id, user, tail, kind))


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


@integration_router.post("/recheck", response_model=PreviewDto, status_code=status.HTTP_202_ACCEPTED)
async def recheck_integration(generation_id: str, user: CurrentUserDep, usecase: PreviewActionUsecaseDep) -> PreviewDto:
    return PreviewDto.from_entity(await usecase.execute_integration(generation_id, user, "recheck"))


@integration_router.post("/use-mocks", response_model=PreviewDto, status_code=status.HTTP_202_ACCEPTED)
async def use_mocks_integration(
    generation_id: str, user: CurrentUserDep, usecase: PreviewActionUsecaseDep
) -> PreviewDto:
    return PreviewDto.from_entity(await usecase.execute_integration(generation_id, user, "use-mocks"))
