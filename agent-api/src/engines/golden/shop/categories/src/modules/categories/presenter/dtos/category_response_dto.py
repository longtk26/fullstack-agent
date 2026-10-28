import uuid

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from src.modules.shared.domain.entities import CategoryEntity


class CategoryResponseDto(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: uuid.UUID
    name: str

    @classmethod
    def from_entity(cls, entity: CategoryEntity) -> "CategoryResponseDto":
        return cls.model_validate(entity.model_dump())
