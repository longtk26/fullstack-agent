import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from src.modules.shared.domain.entities import ContactMessageEntity


class ContactMessageResponseDto(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: uuid.UUID
    name: str
    email: str
    message: str
    created_at: datetime

    @classmethod
    def from_entity(cls, entity: ContactMessageEntity) -> "ContactMessageResponseDto":
        return cls.model_validate(entity.model_dump())
