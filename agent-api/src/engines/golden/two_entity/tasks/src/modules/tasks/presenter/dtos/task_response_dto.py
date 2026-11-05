import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from src.modules.shared.domain.entities import TaskEntity, TaskStatus
from src.modules.shared.presenter.summaries import ProjectSummaryDto, References

# What can be done to a record (Story 10.0b); plugins narrow it by user and state
ALLOWED_ACTIONS: tuple[str, ...] = ("update", "delete")


class TaskResponseDto(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    status: TaskStatus | None
    priority: int | None
    due_date: date | None
    project: ProjectSummaryDto | None
    allowed_actions: list[str]

    @classmethod
    def from_entity(cls, entity: TaskEntity, references: References | None = None) -> "TaskResponseDto":
        refs = references or {}
        return cls.model_validate(
            {
                **entity.model_dump(),
                "project": {"id": entity.project_id, "label": refs.get("project", {}).get(entity.project_id)},
                "allowed_actions": list(ALLOWED_ACTIONS),
            }
        )
