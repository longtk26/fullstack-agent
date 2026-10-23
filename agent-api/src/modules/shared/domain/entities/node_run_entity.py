import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class NodeRunEntity(BaseModel):
    id: uuid.UUID | None = None
    generation_id: str
    node: str
    attempt: int = 1
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    summary: dict[str, Any] = {}
