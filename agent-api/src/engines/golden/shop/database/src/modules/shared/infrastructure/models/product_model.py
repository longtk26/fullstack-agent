import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Numeric, Text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .cart_item_model import CartItemModel
    from .category_model import CategoryModel


class ProductModel(SQLModel, table=True):
    __tablename__ = "products"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    category_id: uuid.UUID = Field(foreign_key="categories.id", ondelete="RESTRICT", index=True)
    name: str = Field(max_length=120)
    description: str | None = Field(default=None, sa_type=Text)
    price: Decimal = Field(sa_type=Numeric(18, 4))
    image_url: str | None = Field(default=None, max_length=500)
    stock: int | None = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), sa_type=DateTime(timezone=True))

    category: "CategoryModel" = Relationship(back_populates="products")
    cart_items: list["CartItemModel"] = Relationship(back_populates="product", passive_deletes="all")
