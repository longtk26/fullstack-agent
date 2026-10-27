from typing import Annotated, Any

from fastapi import Depends

from src.configs import config
from src.libs.exceptions import NotFoundException, ServiceUnavailableException
from src.libs.queue import PreviewCommandTimeout
from src.modules.generations.usecases.get_generation_usecase import GetGenerationUsecaseDep
from src.modules.previews.infrastructure.adapters import PreviewCommandBusDep
from src.modules.previews.ports.output import IPreviewRepoDep
from src.modules.shared.domain.entities import PreviewEntity, UserEntity


class PreviewQueryUsecase:
    """Reads that need the containers (logs, request log) are answered by the worker."""

    def __init__(self, getter: GetGenerationUsecaseDep, preview_repo: IPreviewRepoDep, bus: PreviewCommandBusDep):
        self.getter = getter
        self.preview_repo = preview_repo
        self.bus = bus

    def get(self, generation_id: str, user: UserEntity, kind: str = "backend") -> PreviewEntity:
        self.getter.load(generation_id, user)
        preview = self.preview_repo.find(generation_id, kind)
        if preview is None:
            raise NotFoundException("Preview not found")
        return preview

    async def logs(self, generation_id: str, user: UserEntity, tail: int, kind: str = "backend") -> dict[str, Any]:
        self.get(generation_id, user, kind)
        return await self._call("logs", generation_id, tail=tail, kind=kind)

    async def requests(self, generation_id: str, user: UserEntity, after: str | None, limit: int) -> dict[str, Any]:
        self.get(generation_id, user)
        return await self._call("requests", generation_id, after=after, limit=limit)

    async def _call(self, op: str, generation_id: str, **args: Any) -> dict[str, Any]:
        try:
            return await self.bus.call(op, generation_id, timeout_s=config.preview_command_timeout_seconds, **args)
        except PreviewCommandTimeout as exc:
            raise ServiceUnavailableException(f"No worker answered: {exc}") from exc


class ListPreviewsUsecase:
    def __init__(self, preview_repo: IPreviewRepoDep):
        self.preview_repo = preview_repo

    async def execute(self, user: UserEntity, all_owners: bool) -> list[PreviewEntity]:
        return self.preview_repo.list_for_owner(None if all_owners and user.is_admin else user.id)


PreviewQueryUsecaseDep = Annotated[PreviewQueryUsecase, Depends(PreviewQueryUsecase)]
ListPreviewsUsecaseDep = Annotated[ListPreviewsUsecase, Depends(ListPreviewsUsecase)]
