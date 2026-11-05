from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from src.modules.shared.domain.entities import CartItemEntity
from src.modules.shared.presenter.summaries import References


class ICartItemRepository(ABC):
    @abstractmethod
    def create(self, cart_item: CartItemEntity) -> CartItemEntity:
        pass

    @abstractmethod
    def find_by_id(self, cart_item_id: uuid.UUID) -> CartItemEntity | None:
        pass

    @abstractmethod
    def list(self, sort: tuple[str, bool] | None, limit: int, offset: int) -> tuple[list[CartItemEntity], int]:
        """Returns one page of cart items and the total count."""

    @abstractmethod
    def update(self, cart_item: CartItemEntity) -> CartItemEntity:
        pass

    @abstractmethod
    def delete(self, cart_item_id: uuid.UUID) -> None:
        pass

    @abstractmethod
    def references(self, records: list[CartItemEntity]) -> References:
        """Labels of the records these refer to, one query per reference (Story 10.0b)."""
