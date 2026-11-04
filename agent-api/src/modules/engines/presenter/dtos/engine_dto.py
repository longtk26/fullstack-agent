from datetime import datetime

from src.libs.dtos import CamelModel


class EngineDto(CamelModel):
    name: str
    available: bool
    reason: str | None = None
    drafts_only: bool = False


class ListEnginesResponseDto(CamelModel):
    default: str
    draft_default: str
    engines: list[EngineDto]
    reported_by_worker: bool
    reported_at: datetime | None = None
