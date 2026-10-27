from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Index
from sqlmodel import Field, SQLModel

from ._columns import Json, TZDateTime, utcnow


class GenerationEventModel(SQLModel, table=True):
    __tablename__ = "generation_events"
    __table_args__ = (Index("ix_generation_events_generation_id_id", "generation_id", "id"),)

    id: int | None = Field(default=None, primary_key=True, sa_type=BigInteger)
    generation_id: str = Field(foreign_key="generations.id", ondelete="CASCADE", max_length=32)
    ts: datetime = Field(default_factory=utcnow, sa_type=TZDateTime)
    type: str = Field(max_length=64)
    step: str | None = Field(default=None, max_length=64)
    status: str | None = Field(default=None, max_length=32)
    lane: str | None = Field(default=None, max_length=16)  # backend | frontend | integration (12.2)
    payload: dict[str, Any] = Field(default_factory=dict, sa_type=Json)
