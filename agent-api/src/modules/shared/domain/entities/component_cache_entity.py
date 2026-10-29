from datetime import datetime

from pydantic import BaseModel


class ComponentCacheEntity(BaseModel):
    key: str
    name: str
    source_generation_id: str | None = None
    engine: str
    model: str | None = None
    hits: int = 0
    saved_seconds: float = 0.0
    created_at: datetime | None = None
    last_used_at: datetime | None = None
