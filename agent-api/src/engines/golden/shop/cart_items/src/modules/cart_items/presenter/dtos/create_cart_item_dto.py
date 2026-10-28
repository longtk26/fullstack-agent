import uuid

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from src.modules.shared.domain.entities import CartItemEntity


class CreateCartItemRequestDto(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    product_id: uuid.UUID
    quantity: int = Field(ge=1, le=99)

    def to_entity(self) -> CartItemEntity:
        return CartItemEntity(**self.model_dump())
