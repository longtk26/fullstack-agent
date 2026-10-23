import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Text
from sqlmodel import Field, SQLModel

from ._columns import Json, TZDateTime, utcnow


class SpecDraftModel(SQLModel, table=True):
    __tablename__ = "spec_drafts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(foreign_key="users.id", ondelete="CASCADE", index=True)
    mode: str = Field(default="requirement", max_length=32)
    requirement_text: str | None = Field(default=None, sa_type=Text)
    engine: str = Field(max_length=32)
    status: str = Field(default="PENDING", max_length=32)
    spec_id: uuid.UUID | None = Field(default=None, foreign_key="backend_specs.id", ondelete="SET NULL")
    assumptions: list[Any] = Field(default_factory=list, sa_type=Json)
    unresolved: list[Any] = Field(default_factory=list, sa_type=Json)
    error: str | None = Field(default=None, sa_type=Text)
    created_at: datetime = Field(default_factory=utcnow, sa_type=TZDateTime)
    updated_at: datetime = Field(default_factory=utcnow, sa_type=TZDateTime)
