import uuid
from datetime import datetime

from pydantic import BaseModel

from src.modules.shared.domain.enums import PreviewStatus


class PreviewEntity(BaseModel):
    id: uuid.UUID | None = None
    generation_id: str
    status: PreviewStatus = PreviewStatus.STARTING
    container_id: str | None = None
    db_container_id: str | None = None
    host_port: int | None = None
    url: str | None = None
    started_at: datetime | None = None
    last_accessed_at: datetime | None = None
    expires_at: datetime | None = None
    error: str | None = None
