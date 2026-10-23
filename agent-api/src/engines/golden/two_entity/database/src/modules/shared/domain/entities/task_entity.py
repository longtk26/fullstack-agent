import uuid
from datetime import date
from enum import StrEnum

from pydantic import BaseModel


class TaskStatus(StrEnum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"


class TaskEntity(BaseModel):
    id: uuid.UUID | None = None
    project_id: uuid.UUID
    title: str
    status: TaskStatus | None = TaskStatus.TODO
    priority: int | None = 3
    due_date: date | None = None
