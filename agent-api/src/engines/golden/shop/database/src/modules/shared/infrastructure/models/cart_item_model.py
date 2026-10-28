import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .product_model import ProductModel


class CartItemModel(SQLModel, table=True):
    __tablename__ = "cart_items"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    product_id: uuid.UUID = Field(foreign_key="products.id", ondelete="CASCADE", index=True)
    quantity: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), sa_type=DateTime(timezone=True))

    product: "ProductModel" = Relationship(back_populates="cart_items")
