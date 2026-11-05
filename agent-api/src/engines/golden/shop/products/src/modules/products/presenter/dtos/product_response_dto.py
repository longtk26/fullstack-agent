import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from src.modules.shared.domain.entities import ProductEntity
from src.modules.shared.presenter.summaries import CategorySummaryDto, References

# What can be done to a record (Story 10.0b); plugins narrow it by user and state
ALLOWED_ACTIONS: tuple[str, ...] = ()


class ProductResponseDto(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: uuid.UUID
    category_id: uuid.UUID
    name: str
    description: str | None
    price: float
    image_url: str | None
    stock: int | None
    created_at: datetime
    category: CategorySummaryDto | None
    allowed_actions: list[str]

    @classmethod
    def from_entity(cls, entity: ProductEntity, references: References | None = None) -> "ProductResponseDto":
        refs = references or {}
        return cls.model_validate(
            {
                **entity.model_dump(),
                "price": float(entity.price),
                "category": {"id": entity.category_id, "label": refs.get("category", {}).get(entity.category_id)},
                "allowed_actions": list(ALLOWED_ACTIONS),
            }
        )
