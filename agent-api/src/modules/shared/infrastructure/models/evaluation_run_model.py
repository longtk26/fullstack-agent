import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Text
from sqlmodel import Field, SQLModel

from ._columns import Json, TZDateTime, utcnow


class EvaluationRunModel(SQLModel, table=True):
    """Story 26.5: one business evaluation of a generation. Information only: it never changes the generation."""

    __tablename__ = "evaluation_runs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    generation_id: str = Field(foreign_key="generations.id", ondelete="CASCADE", index=True, max_length=32)
    status: str = Field(default="PENDING", max_length=16)  # PENDING | RUNNING | DONE | FAILED
    trigger: str = Field(default="auto", max_length=16)  # auto | manual
    provider: str | None = Field(default=None, max_length=32)
    # Story 26.7: the generation whose frozen expectations this run checks (empty: this generation's own draft)
    expectations_from: str | None = Field(default=None, max_length=32)
    score: dict[str, Any] | None = Field(default=None, sa_type=Json)
    report: dict[str, Any] | None = Field(default=None, sa_type=Json)
    usage: dict[str, Any] | None = Field(default=None, sa_type=Json)
    progress: str | None = Field(default=None, max_length=128)
    error: str | None = Field(default=None, sa_type=Text)
    created_at: datetime = Field(default_factory=utcnow, sa_type=TZDateTime)
    started_at: datetime | None = Field(default=None, sa_type=TZDateTime)
    finished_at: datetime | None = Field(default=None, sa_type=TZDateTime)
