from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from src.modules.shared.domain.entities import ContactMessageEntity


class CreateContactMessageRequestDto(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=1, max_length=254)
    message: str = Field(min_length=1)

    def to_entity(self) -> ContactMessageEntity:
        return ContactMessageEntity(**self.model_dump())
