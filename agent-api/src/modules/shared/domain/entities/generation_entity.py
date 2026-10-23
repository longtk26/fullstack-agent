import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from src.modules.shared.domain.enums import GenerationStatus


class GenerationEntity(BaseModel):
    id: str
    owner_id: uuid.UUID
    spec_id: uuid.UUID
    options: dict[str, Any] = {}
    engine: str
    status: GenerationStatus = GenerationStatus.PENDING
    current_step: str | None = None
    repair_attempts: int = 0
    trace_id: str | None = None
    langsmith_run_url: str | None = None
    error_summary: str | None = None
    cancel_requested: bool = False
    resume_count: int = 0
    worker_id: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    heartbeat_at: datetime | None = None
