import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ValidationRunEntity(BaseModel):
    id: uuid.UUID | None = None
    generation_id: str
    attempt: int = 0
    check: str
    status: str
    started_at: datetime | None = None
    duration_ms: int | None = None
    output_ref: str | None = None
    details: dict[str, Any] = {}
    created_at: datetime | None = None
