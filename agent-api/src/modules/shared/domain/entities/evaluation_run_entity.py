import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class EvaluationRunEntity(BaseModel):
    """Story 26.5: a business evaluation of a generation (information only)."""

    id: uuid.UUID | None = None
    generation_id: str
    status: str = "PENDING"
    trigger: str = "auto"
    provider: str | None = None
    expectations_from: str | None = None  # Story 26.7: another generation's expectations
    score: dict[str, Any] | None = None
    report: dict[str, Any] | None = None
    usage: dict[str, Any] | None = None
    progress: str | None = None
    error: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
