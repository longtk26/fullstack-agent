import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from src.modules.shared.domain.entities import TaskEntity, TaskStatus


class UpdateTaskRequestDto(BaseModel):
    """PATCH body: only the fields that are sent change."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    project_id: uuid.UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    status: TaskStatus | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    due_date: date | None = None

    def to_entity(self, current: TaskEntity) -> TaskEntity:
        return current.model_copy(update=self.model_dump(exclude_unset=True))
