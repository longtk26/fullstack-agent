import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from src.modules.shared.domain.entities import ProjectEntity

# What can be done to a record (Story 10.0b); plugins narrow it by user and state
ALLOWED_ACTIONS: tuple[str, ...] = ("update", "delete")


class ProjectResponseDto(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    allowed_actions: list[str]

    @classmethod
    def from_entity(cls, entity: ProjectEntity) -> "ProjectResponseDto":
        return cls.model_validate(
            {
                **entity.model_dump(),
                "allowed_actions": list(ALLOWED_ACTIONS),
            }
        )
