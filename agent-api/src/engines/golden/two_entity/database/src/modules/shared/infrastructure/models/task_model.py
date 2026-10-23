import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, Relationship, SQLModel

from src.modules.shared.domain.entities import TaskStatus

if TYPE_CHECKING:
    from .project_model import ProjectModel


class TaskModel(SQLModel, table=True):
    __tablename__ = "tasks"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="projects.id", ondelete="CASCADE", index=True)
    title: str = Field(max_length=200)
    status: TaskStatus | None = Field(
        default=TaskStatus.TODO,
        sa_type=SAEnum(TaskStatus, name="task_status", values_callable=lambda e: [m.value for m in e]),
    )
    priority: int | None = Field(default=3)
    due_date: date | None = None

    project: "ProjectModel" = Relationship(back_populates="tasks")
