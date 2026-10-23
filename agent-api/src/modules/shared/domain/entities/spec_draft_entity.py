import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from src.modules.shared.domain.enums import SpecDraftStatus, SpecSource


class SpecDraftEntity(BaseModel):
    id: uuid.UUID | None = None
    owner_id: uuid.UUID
    mode: SpecSource = SpecSource.REQUIREMENT
    requirement_text: str | None = None
    engine: str
    status: SpecDraftStatus = SpecDraftStatus.PENDING
    spec_id: uuid.UUID | None = None
    assumptions: list[Any] = []
    unresolved: list[Any] = []
    error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
