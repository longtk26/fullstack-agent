import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from src.modules.shared.domain.entities import CartItemEntity


class CartItemResponseDto(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    created_at: datetime

    @classmethod
    def from_entity(cls, entity: CartItemEntity) -> "CartItemResponseDto":
        return cls.model_validate(entity.model_dump())
