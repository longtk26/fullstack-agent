import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from src.modules.shared.domain.entities import TaskEntity, TaskStatus


class CreateTaskRequestDto(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    project_id: uuid.UUID
    title: str = Field(min_length=1, max_length=200)
    status: TaskStatus | None = TaskStatus.TODO
    priority: int | None = Field(default=3, ge=1, le=5)
    due_date: date | None = None

    def to_entity(self) -> TaskEntity:
        return TaskEntity(**self.model_dump())
