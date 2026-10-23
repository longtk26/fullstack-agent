import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Text
from sqlmodel import Field, SQLModel

from ._columns import Json, TZDateTime, utcnow


class BackendSpecModel(SQLModel, table=True):
    __tablename__ = "backend_specs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(foreign_key="users.id", ondelete="CASCADE", index=True)
    spec_version: str = Field(max_length=16)
    raw_json: str = Field(sa_type=Text)
    normalized_json: dict[str, Any] | None = Field(default=None, sa_type=Json)
    source: str = Field(default="json", max_length=32)
    requirement_text: str | None = Field(default=None, sa_type=Text)
    created_at: datetime = Field(default_factory=utcnow, sa_type=TZDateTime)
