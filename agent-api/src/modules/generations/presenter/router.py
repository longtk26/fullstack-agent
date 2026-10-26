from typing import Annotated, Any

from fastapi import APIRouter, Header, Query, status
from fastapi.responses import FileResponse
from sse_starlette import EventSourceResponse

from src.modules.auth.presenter import CurrentUserDep
from src.modules.generations.presenter.dtos import (
    ArtifactDto,
    ArtifactListDto,
    CancelGenerationResponseDto,
    CreateGenerationRequestDto,
    CreateGenerationResponseDto,
    GenerationDetailDto,
    GenerationPageDto,
    GenerationSummaryDto,
)
from src.modules.generations.usecases import (
    ArtifactUsecaseDep,
    BrowseFilesUsecaseDep,
    CancelGenerationUsecaseDep,
    CreateGenerationUsecaseDep,
    GetGenerationUsecaseDep,
    GetValidationUsecaseDep,
    GetWorkflowGraphUsecaseDep,
    ListGenerationsUsecaseDep,
    StreamGenerationEventsUsecaseDep,
)
from src.modules.shared.domain.enums import GenerationStatus

generation_router = APIRouter(prefix="/api/v1/generations", tags=["generations"])


@generation_router.post("", response_model=CreateGenerationResponseDto, status_code=status.HTTP_202_ACCEPTED)
async def create_generation(
    body: CreateGenerationRequestDto,
    user: CurrentUserDep,
    usecase: CreateGenerationUsecaseDep,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", max_length=128)] = None,
) -> CreateGenerationResponseDto:
    generation = await usecase.execute(
        user, body.backend_spec, body.spec_id, body.options.model_dump(by_alias=True), idempotency_key
    )
    return CreateGenerationResponseDto(
        generation_id=generation.id, status=generation.status, created_at=generation.created_at
    )


@generation_router.get("", response_model=GenerationPageDto)
async def list_generations(
    user: CurrentUserDep,
    usecase: ListGenerationsUsecaseDep,
    status_filter: Annotated[GenerationStatus | None, Query(alias="status")] = None,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    scope: Annotated[str, Query(pattern="^(mine|all)$")] = "mine",
) -> GenerationPageDto:
    page = await usecase.execute(user, status_filter, cursor, limit, all_owners=scope == "all")
    return GenerationPageDto(
        items=[
            GenerationSummaryDto(
                generation_id=item.generation.id,
                project_name=item.project_name,
                status=item.generation.status,
                current_step=item.generation.current_step,
                engine=item.generation.engine,
                repair_attempts=item.generation.repair_attempts,
                created_at=item.generation.created_at,
                started_at=item.generation.started_at,
                finished_at=item.generation.finished_at,
            )
            for item in page.items
        ],
        next_cursor=page.next_cursor,
    )


@generation_router.get("/graph", response_model=dict[str, Any])
async def get_workflow_graph(_: CurrentUserDep, usecase: GetWorkflowGraphUsecaseDep) -> dict[str, Any]:
    return await usecase.execute()


@generation_router.get("/{generation_id}", response_model=GenerationDetailDto)
async def get_generation(generation_id: str, user: CurrentUserDep, usecase: GetGenerationUsecaseDep):
    return GenerationDetailDto.from_detail(await usecase.execute(generation_id, user))


@generation_router.post(
    "/{generation_id}/cancel", response_model=CancelGenerationResponseDto, status_code=status.HTTP_202_ACCEPTED
)
async def cancel_generation(
    generation_id: str, user: CurrentUserDep, usecase: CancelGenerationUsecaseDep
) -> CancelGenerationResponseDto:
    generation = await usecase.execute(generation_id, user)
    return CancelGenerationResponseDto(
        generation_id=generation.id, status=generation.status, cancel_requested=generation.cancel_requested
    )


@generation_router.get("/{generation_id}/events")
async def stream_generation_events(
    generation_id: str,
    user: CurrentUserDep,
    usecase: StreamGenerationEventsUsecaseDep,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
    after: Annotated[int | None, Query(ge=0)] = None,
) -> EventSourceResponse:
    start = int(last_event_id) if last_event_id and last_event_id.isdigit() else (after or 0)
    return EventSourceResponse(await usecase.execute(generation_id, user, start), ping=15)


@generation_router.get("/{generation_id}/validation", response_model=dict[str, Any])
async def get_validation(generation_id: str, user: CurrentUserDep, usecase: GetValidationUsecaseDep) -> dict[str, Any]:
    return await usecase.execute(generation_id, user)


@generation_router.get("/{generation_id}/artifacts", response_model=ArtifactListDto)
async def list_artifacts(generation_id: str, user: CurrentUserDep, usecase: ArtifactUsecaseDep) -> ArtifactListDto:
    return ArtifactListDto(items=[ArtifactDto.from_entity(a) for a in await usecase.list(generation_id, user)])


@generation_router.get("/{generation_id}/artifacts/{artifact_id}", response_class=FileResponse)
async def download_artifact(
    generation_id: str, artifact_id: str, user: CurrentUserDep, usecase: ArtifactUsecaseDep
) -> FileResponse:
    artifact, path = await usecase.file(generation_id, artifact_id, user)
    return FileResponse(path, media_type=artifact.content_type, filename=artifact.name)


@generation_router.get("/{generation_id}/files", response_model=dict[str, Any])
async def browse_files(
    generation_id: str,
    user: CurrentUserDep,
    usecase: BrowseFilesUsecaseDep,
    path: Annotated[str, Query(max_length=512)] = "",
) -> dict[str, Any]:
    return await usecase.execute(generation_id, user, path)
