from datetime import datetime

from src.libs.dtos import CamelModel


class EngineDto(CamelModel):
    name: str
    available: bool
    reason: str | None = None
    drafts_only: bool = False
    drafts: bool = False  # Story 22.8: may draft specs (the draft engine picker lists only these)


class ListEnginesResponseDto(CamelModel):
    default: str
    draft_default: str | None
    engines: list[EngineDto]
    reported_by_worker: bool
    reported_at: datetime | None = None
