import uuid
from datetime import datetime
from typing import Any

from sqlmodel import Field, SQLModel

from ._columns import Json, TZDateTime, utcnow


class NodeRunModel(SQLModel, table=True):
    __tablename__ = "node_runs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    generation_id: str = Field(foreign_key="generations.id", ondelete="CASCADE", index=True, max_length=32)
    node: str = Field(max_length=64)
    attempt: int = 1
    status: str = Field(max_length=32)
    started_at: datetime = Field(default_factory=utcnow, sa_type=TZDateTime)
    finished_at: datetime | None = Field(default=None, sa_type=TZDateTime)
    summary: dict[str, Any] = Field(default_factory=dict, sa_type=Json)
