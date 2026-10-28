"""Imports every ORM model so Alembic autogenerate discovers it (fastapi-skills pillar 4)."""

from src.modules.shared.infrastructure.models import (
    CartItemModel,
    CategoryModel,
    ContactMessageModel,
    ProductModel,
)

__all__ = ["CartItemModel", "CategoryModel", "ContactMessageModel", "ProductModel"]
