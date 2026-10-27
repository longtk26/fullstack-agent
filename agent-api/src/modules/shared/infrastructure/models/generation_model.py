import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Index, Text
from sqlmodel import Field, SQLModel

from src.modules.shared.domain.enums import GenerationStatus

from ._columns import Json, TZDateTime, utcnow


class GenerationModel(SQLModel, table=True):
    __tablename__ = "generations"
    __table_args__ = (Index("ix_generations_owner_id_created_at", "owner_id", "created_at"),)

    id: str = Field(primary_key=True, max_length=32)
    owner_id: uuid.UUID = Field(foreign_key="users.id", ondelete="CASCADE")
    spec_id: uuid.UUID = Field(foreign_key="backend_specs.id", ondelete="RESTRICT", index=True)
    options: dict[str, Any] = Field(default_factory=dict, sa_type=Json)
    engine: str = Field(max_length=32)
    status: GenerationStatus = Field(
        default=GenerationStatus.PENDING, sa_type=SAEnum(GenerationStatus, name="generation_status"), index=True
    )
    current_step: str | None = Field(default=None, max_length=64)
    repair_attempts: int = 0
    trace_id: str | None = Field(default=None, max_length=64)
    langsmith_run_url: str | None = None
    # LangSmith dotted order of the root run, so a resumed job keeps adding to the same trace (Story 8.1)
    trace_parent: str | None = Field(default=None, max_length=128)
    error_summary: str | None = Field(default=None, sa_type=Text)
    cancel_requested: bool = False
    resume_count: int = 0
    worker_id: str | None = Field(default=None, max_length=64)
    created_at: datetime = Field(default_factory=utcnow, sa_type=TZDateTime)
    started_at: datetime | None = Field(default=None, sa_type=TZDateTime)
    finished_at: datetime | None = Field(default=None, sa_type=TZDateTime)
    heartbeat_at: datetime | None = Field(default=None, sa_type=TZDateTime)
