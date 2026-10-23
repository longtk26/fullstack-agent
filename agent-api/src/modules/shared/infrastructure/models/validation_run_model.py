import uuid
from datetime import datetime
from typing import Any

from sqlmodel import Field, SQLModel

from ._columns import Json, TZDateTime, utcnow


class ValidationRunModel(SQLModel, table=True):
    __tablename__ = "validation_runs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    generation_id: str = Field(foreign_key="generations.id", ondelete="CASCADE", index=True, max_length=32)
    attempt: int = 0
    check: str = Field(max_length=32)
    status: str = Field(max_length=32)
    duration_ms: int | None = None
    output_ref: str | None = None
    details: dict[str, Any] = Field(default_factory=dict, sa_type=Json)
    created_at: datetime = Field(default_factory=utcnow, sa_type=TZDateTime)
