import uuid

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from src.modules.shared.domain.entities import CategoryEntity

# What can be done to a record (Story 10.0b); plugins narrow it by user and state
ALLOWED_ACTIONS: tuple[str, ...] = ()


class CategoryResponseDto(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: uuid.UUID
    name: str
    allowed_actions: list[str]

    @classmethod
    def from_entity(cls, entity: CategoryEntity) -> "CategoryResponseDto":
        return cls.model_validate(
            {
                **entity.model_dump(),
                "allowed_actions": list(ALLOWED_ACTIONS),
            }
        )
