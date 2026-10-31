import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ImageCallEntity(BaseModel):
    """One AI photo generation request (Story 19.2)."""

    id: uuid.UUID
    generation_id: str | None = None
    draft_id: uuid.UUID | None = None
    node_run_id: uuid.UUID | None = None
    asset_id: str
    model: str
    status: Literal["ok", "cached", "blocked", "failed"]
    duration_ms: int = 0
    cost_usd: float | None = None
    error: str | None = None
    created_at: datetime | None = None
