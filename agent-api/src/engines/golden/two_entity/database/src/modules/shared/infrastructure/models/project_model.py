import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .task_model import TaskModel


class ProjectModel(SQLModel, table=True):
    __tablename__ = "projects"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=120, unique=True)
    description: str | None = Field(default=None, sa_type=Text)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), sa_type=DateTime(timezone=True))

    # The database cascades the delete (ondelete="CASCADE"); the ORM must not null the children first.
    tasks: list["TaskModel"] = Relationship(back_populates="project", passive_deletes="all")
