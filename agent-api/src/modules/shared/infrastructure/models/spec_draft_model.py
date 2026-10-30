import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Text
from sqlmodel import Field, SQLModel

from ._columns import Json, TZDateTime, utcnow


class SpecDraftModel(SQLModel, table=True):
    """A drafting job (Stories 2.4, 12.4): requirement (or frontend site JSON) → draft spec(s), run by the worker."""

    __tablename__ = "spec_drafts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(foreign_key="users.id", ondelete="CASCADE", index=True)
    source: str = Field(default="requirement", max_length=32)  # requirement | frontend (2.5 "Refine with AI")
    mode: str = Field(default="backend", max_length=32)  # generation mode the draft is for
    requirement_text: str | None = Field(default=None, sa_type=Text)
    requirement_format: str | None = Field(default=None, max_length=16)
    requirement_file_name: str | None = Field(default=None, max_length=255)
    inputs: dict[str, Any] = Field(default_factory=dict, sa_type=Json)  # source=frontend: baseSpec, siteJson
    engine: str = Field(max_length=32)
    status: str = Field(default="PENDING", max_length=32, index=True)
    progress: str | None = Field(default=None, max_length=64)
    attempts: int = 0
    spec_id: uuid.UUID | None = Field(default=None, foreign_key="backend_specs.id", ondelete="SET NULL")
    # JSON, not JSONB: the drafted specs keep the key order the engine wrote, so the editor shows them as written.
    backend_spec: dict[str, Any] | None = Field(default=None, sa_type=JSON)
    frontend_spec: dict[str, Any] | None = Field(default=None, sa_type=JSON)
    assumptions: list[Any] = Field(default_factory=list, sa_type=Json)
    unresolved: list[Any] = Field(default_factory=list, sa_type=Json)
    validation: dict[str, Any] = Field(default_factory=dict, sa_type=Json)
    usage: dict[str, Any] = Field(default_factory=dict, sa_type=Json)
    error: str | None = Field(default=None, sa_type=Text)
    worker_id: str | None = Field(default=None, max_length=64)
    created_at: datetime = Field(default_factory=utcnow, sa_type=TZDateTime, index=True)
    updated_at: datetime = Field(default_factory=utcnow, sa_type=TZDateTime)
    started_at: datetime | None = Field(default=None, sa_type=TZDateTime)
    finished_at: datetime | None = Field(default=None, sa_type=TZDateTime)
