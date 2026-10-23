import uuid

from fastapi import APIRouter, Query, status

from src.modules.shared.domain.entities import TaskStatus
from src.modules.tasks.presenter.dtos import (
    CreateTaskRequestDto,
    ListTasksResponseDto,
    TaskResponseDto,
    UpdateTaskRequestDto,
)
from src.modules.tasks.usecases import (
    CreateTaskUsecaseDep,
    DeleteTaskUsecaseDep,
    GetTaskUsecaseDep,
    ListTasksUsecaseDep,
    UpdateTaskUsecaseDep,
)

task_router = APIRouter(tags=["tasks"])

ERROR = {"description": "Error envelope: {error: {code, message, details}}"}


@task_router.post(
    "/tasks",
    operation_id="task.create",
    response_model=TaskResponseDto,
    status_code=status.HTTP_201_CREATED,
    responses={400: ERROR, 422: ERROR},
)
async def create_task(body: CreateTaskRequestDto, usecase: CreateTaskUsecaseDep) -> TaskResponseDto:
    return await usecase.execute(body)


@task_router.get("/tasks/{id}", operation_id="task.get", response_model=TaskResponseDto, responses={404: ERROR})
async def get_task(id: uuid.UUID, usecase: GetTaskUsecaseDep) -> TaskResponseDto:
    return await usecase.execute(id)


@task_router.get("/tasks", operation_id="task.list", response_model=ListTasksResponseDto, responses={422: ERROR})
async def list_tasks(
    usecase: ListTasksUsecaseDep,
    project_id: uuid.UUID | None = Query(default=None, alias="projectId"),
    task_status: TaskStatus | None = Query(default=None, alias="status"),
    sort: str | None = Query(default=None, pattern=r"^-?(priority|dueDate)$"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ListTasksResponseDto:
    return await usecase.execute(project_id, task_status, sort, limit, offset)


@task_router.patch(
    "/tasks/{id}",
    operation_id="task.update",
    response_model=TaskResponseDto,
    responses={400: ERROR, 404: ERROR, 422: ERROR},
)
async def update_task(id: uuid.UUID, body: UpdateTaskRequestDto, usecase: UpdateTaskUsecaseDep) -> TaskResponseDto:
    return await usecase.execute(id, body)


@task_router.delete(
    "/tasks/{id}", operation_id="task.delete", status_code=status.HTTP_204_NO_CONTENT, responses={404: ERROR}
)
async def delete_task(id: uuid.UUID, usecase: DeleteTaskUsecaseDep) -> None:
    await usecase.execute(id)
