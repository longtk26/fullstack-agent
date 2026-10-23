import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from src.modules.shared.domain.entities import TaskEntity, TaskStatus


class TaskResponseDto(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    status: TaskStatus | None
    priority: int | None
    due_date: date | None

    @classmethod
    def from_entity(cls, entity: TaskEntity) -> "TaskResponseDto":
        return cls.model_validate(entity.model_dump())
