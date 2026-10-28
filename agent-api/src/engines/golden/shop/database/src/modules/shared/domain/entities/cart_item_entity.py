import uuid
from datetime import datetime

from pydantic import BaseModel


class CartItemEntity(BaseModel):
    id: uuid.UUID | None = None
    product_id: uuid.UUID
    quantity: int
    created_at: datetime | None = None
