from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import Depends

from src.configs import config
from src.libs.decorators.transactional_decorator import Transactional
from src.libs.exceptions import ConflictException, ErrorCode, NotFoundException
from src.modules.generations.ports.output import IArtifactRepoDep
from src.modules.generations.usecases.get_generation_usecase import GetGenerationUsecaseDep
from src.modules.previews.infrastructure.adapters import PreviewCommandBusDep
from src.modules.previews.ports.output import IPreviewRepoDep
from src.modules.shared.domain.entities import PreviewEntity, UserEntity
from src.modules.shared.domain.enums import GenerationStatus, PreviewStatus

PreviewAction = Literal["start", "stop", "restart", "delete", "reset-db"]
SOURCE_ARTIFACT = "backend.zip"
ACTIVE = (PreviewStatus.STARTING, PreviewStatus.RUNNING)


class PreviewActionUsecase:
    """Validates and records the request; the worker does the Docker work and reports back via the previews row
    and `preview.status` events."""

    def __init__(
        self,
        getter: GetGenerationUsecaseDep,
        preview_repo: IPreviewRepoDep,
        artifact_repo: IArtifactRepoDep,
        bus: PreviewCommandBusDep,
    ):
        self.getter = getter
        self.preview_repo = preview_repo
        self.artifact_repo = artifact_repo
        self.bus = bus

    async def execute(self, generation_id: str, user: UserEntity, action: PreviewAction) -> PreviewEntity | None:
        generation = self.getter.load(generation_id, user)
        if not config.preview_enabled:
            raise ConflictException("Previews are disabled (PREVIEW_ENABLED=false)", code=ErrorCode.PREVIEWS_DISABLED)
        preview = self.preview_repo.find(generation_id)
        if action in ("stop", "delete"):
            if preview is None:
                raise NotFoundException("Preview not found")
            await self.bus.send(action, generation_id)
            return preview if action == "stop" else None

        if generation.status != GenerationStatus.COMPLETED:
            raise ConflictException(
                f"Only COMPLETED generations have a preview (status {generation.status})",
                code=ErrorCode.GENERATION_NOT_COMPLETED,
            )
        if self.artifact_repo.find_by_name(generation_id, SOURCE_ARTIFACT) is None:
            raise ConflictException("The generation has no packaged source", code=ErrorCode.ARTIFACT_MISSING)
        if action == "start" and preview is not None and preview.status in ACTIVE:
            return preview
        if not config.preview_evict and not (preview and preview.status in ACTIVE):
            running = [p for p in self.preview_repo.list_by_status(ACTIVE) if p.generation_id != generation_id]
            if len(running) >= config.preview_max_running:
                raise ConflictException(
                    f"{len(running)} previews are running (PREVIEW_MAX_RUNNING={config.preview_max_running}); "
                    "stop one first",
                    code=ErrorCode.PREVIEW_LIMIT_REACHED,
                )
        preview = await self._mark_starting(generation_id)
        await self.bus.send(action, generation_id)
        return preview

    @Transactional
    async def _mark_starting(self, generation_id: str) -> PreviewEntity:
        return self.preview_repo.upsert(
            generation_id, status=PreviewStatus.STARTING, started_at=datetime.now(UTC), error=None
        )


class TouchPreviewUsecase:
    def __init__(self, getter: GetGenerationUsecaseDep, preview_repo: IPreviewRepoDep):
        self.getter = getter
        self.preview_repo = preview_repo

    @Transactional
    async def execute(self, generation_id: str, user: UserEntity) -> PreviewEntity:
        self.getter.load(generation_id, user)
        preview = self.preview_repo.find(generation_id)
        if preview is None:
            raise NotFoundException("Preview not found")
        if preview.status != PreviewStatus.RUNNING:
            raise ConflictException(f"Preview is {preview.status}", code=ErrorCode.PREVIEW_NOT_RUNNING)
        now = datetime.now(UTC)
        return self.preview_repo.upsert(
            generation_id, last_accessed_at=now, expires_at=now + timedelta(hours=config.preview_ttl_hours)
        )


PreviewActionUsecaseDep = Annotated[PreviewActionUsecase, Depends(PreviewActionUsecase)]
TouchPreviewUsecaseDep = Annotated[TouchPreviewUsecase, Depends(TouchPreviewUsecase)]
