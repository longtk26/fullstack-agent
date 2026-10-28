import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from src.modules.shared.domain.entities import ProductEntity


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

    @classmethod
    def from_entity(cls, entity: ProductEntity) -> "ProductResponseDto":
        return cls.model_validate({**entity.model_dump(), "price": float(entity.price)})
