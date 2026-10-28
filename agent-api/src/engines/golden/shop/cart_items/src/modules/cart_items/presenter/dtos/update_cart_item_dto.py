import uuid

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from src.modules.shared.domain.entities import CartItemEntity


class UpdateCartItemRequestDto(BaseModel):
    """PATCH body: only the fields that are sent change."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    product_id: uuid.UUID | None = None
    quantity: int | None = Field(default=None, ge=1, le=99)

    def to_entity(self, current: CartItemEntity) -> CartItemEntity:
        return current.model_copy(update=self.model_dump(exclude_unset=True))
