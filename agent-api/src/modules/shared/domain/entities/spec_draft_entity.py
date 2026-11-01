import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from src.modules.shared.domain.enums import GenerationMode, SpecDraftStatus, SpecSource


class SpecDraftEntity(BaseModel):
    id: uuid.UUID | None = None
    owner_id: uuid.UUID
    source: SpecSource = SpecSource.REQUIREMENT
    mode: GenerationMode = GenerationMode.BACKEND
    requirement_text: str | None = None
    requirement_format: str | None = None
    requirement_file_name: str | None = None
    inputs: dict[str, Any] = {}
    engine: str
    status: SpecDraftStatus = SpecDraftStatus.PENDING
    progress: str | None = None
    attempts: int = 0
    spec_id: uuid.UUID | None = None
    backend_spec: dict[str, Any] | None = None
    frontend_spec: dict[str, Any] | None = None
    assumptions: list[Any] = []
    unresolved: list[Any] = []
    design: dict[str, Any] | None = None
    validation: dict[str, Any] = {}
    usage: dict[str, Any] = {}
    error: str | None = None
    worker_id: str | None = None
    generation_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_DRAFT_STATUSES


TERMINAL_DRAFT_STATUSES = frozenset(
    {SpecDraftStatus.SUCCEEDED, SpecDraftStatus.NEEDS_REVIEW, SpecDraftStatus.FAILED, SpecDraftStatus.CANCELLED}
)
