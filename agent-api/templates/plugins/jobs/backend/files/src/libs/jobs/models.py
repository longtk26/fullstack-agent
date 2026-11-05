import datetime as dt
import uuid
from typing import Any

from sqlalchemy import DateTime, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class JobModel(SQLModel, table=True):
    """A queued job (Story 10.6). `status`: queued → running → done, or back to queued to retry, or dead."""

    __tablename__ = "job_queue"
    __table_args__ = (Index("ix_job_queue_due", "status", "run_at"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    kind: str = Field(max_length=120, index=True)
    payload: dict[str, Any] = Field(default_factory=dict, sa_type=JSONB)
    status: str = Field(default="queued", max_length=16)
    attempts: int = 0
    max_attempts: int = 5
    run_at: dt.datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
    locked_by: str | None = Field(default=None, max_length=120)
    locked_at: dt.datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    last_error: str | None = Field(default=None, sa_type=Text)
    dedupe_key: str | None = Field(default=None, max_length=255, unique=True)
    created_at: dt.datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
    finished_at: dt.datetime | None = Field(default=None, sa_type=DateTime(timezone=True))


class JobScheduleModel(SQLModel, table=True):
    """When a cron job is next due; the worker that takes the row enqueues it once and moves it on."""

    __tablename__ = "job_schedules"

    name: str = Field(primary_key=True, max_length=120)
    cron: str = Field(max_length=120)
    next_run_at: dt.datetime = Field(sa_type=DateTime(timezone=True))
