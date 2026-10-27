from datetime import datetime
from typing import Any

from pydantic import BaseModel


class GenerationEventEntity(BaseModel):
    id: int | None = None
    generation_id: str
    ts: datetime | None = None
    type: str
    step: str | None = None
    status: str | None = None
    lane: str | None = None
    payload: dict[str, Any] = {}
