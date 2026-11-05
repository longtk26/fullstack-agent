import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from src.modules.shared.domain.entities import CartItemEntity
from src.modules.shared.presenter.summaries import ProductSummaryDto, References

# What can be done to a record (Story 10.0b); plugins narrow it by user and state
ALLOWED_ACTIONS: tuple[str, ...] = ("update", "delete")


class CartItemResponseDto(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    created_at: datetime
    product: ProductSummaryDto | None
    allowed_actions: list[str]

    @classmethod
    def from_entity(cls, entity: CartItemEntity, references: References | None = None) -> "CartItemResponseDto":
        refs = references or {}
        return cls.model_validate(
            {
                **entity.model_dump(),
                "product": {"id": entity.product_id, "label": refs.get("product", {}).get(entity.product_id)},
                "allowed_actions": list(ALLOWED_ACTIONS),
            }
        )
