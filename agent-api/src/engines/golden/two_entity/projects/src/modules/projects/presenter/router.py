import uuid

from fastapi import APIRouter, Query, status

from src.modules.projects.presenter.dtos import (
    CreateProjectRequestDto,
    ListProjectsResponseDto,
    ProjectResponseDto,
    UpdateProjectRequestDto,
)
from src.modules.projects.usecases import (
    CreateProjectUsecaseDep,
    DeleteProjectUsecaseDep,
    GetProjectUsecaseDep,
    ListProjectsUsecaseDep,
    UpdateProjectUsecaseDep,
)

project_router = APIRouter(tags=["projects"])

ERROR = {"description": "Error envelope: {error: {code, message, details}}"}


@project_router.post(
    "/projects",
    operation_id="project.create",
    response_model=ProjectResponseDto,
    status_code=status.HTTP_201_CREATED,
    responses={409: ERROR, 422: ERROR},
)
async def create_project(body: CreateProjectRequestDto, usecase: CreateProjectUsecaseDep) -> ProjectResponseDto:
    return await usecase.execute(body)


@project_router.get(
    "/projects/{id}", operation_id="project.get", response_model=ProjectResponseDto, responses={404: ERROR}
)
async def get_project(id: uuid.UUID, usecase: GetProjectUsecaseDep) -> ProjectResponseDto:
    return await usecase.execute(id)


@project_router.get(
    "/projects", operation_id="project.list", response_model=ListProjectsResponseDto, responses={422: ERROR}
)
async def list_projects(
    usecase: ListProjectsUsecaseDep,
    sort: str | None = Query(default=None, pattern=r"^-?(name|createdAt)$"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ListProjectsResponseDto:
    return await usecase.execute(sort, limit, offset)


@project_router.patch(
    "/projects/{id}",
    operation_id="project.update",
    response_model=ProjectResponseDto,
    responses={404: ERROR, 409: ERROR, 422: ERROR},
)
async def update_project(
    id: uuid.UUID, body: UpdateProjectRequestDto, usecase: UpdateProjectUsecaseDep
) -> ProjectResponseDto:
    return await usecase.execute(id, body)


@project_router.delete(
    "/projects/{id}", operation_id="project.delete", status_code=status.HTTP_204_NO_CONTENT, responses={404: ERROR}
)
async def delete_project(id: uuid.UUID, usecase: DeleteProjectUsecaseDep) -> None:
    await usecase.execute(id)
