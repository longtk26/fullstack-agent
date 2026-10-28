import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class ProductEntity(BaseModel):
    id: uuid.UUID | None = None
    category_id: uuid.UUID
    name: str
    description: str | None = None
    price: Decimal
    image_url: str | None = None
    stock: int | None = 0
    created_at: datetime | None = None
