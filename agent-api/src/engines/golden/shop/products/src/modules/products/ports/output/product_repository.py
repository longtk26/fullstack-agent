from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from src.modules.shared.domain.entities import ProductEntity
from src.modules.shared.presenter.summaries import References


class IProductRepository(ABC):
    @abstractmethod
    def find_by_id(self, product_id: uuid.UUID) -> ProductEntity | None:
        pass

    @abstractmethod
    def list(
        self,
        category_id: uuid.UUID | None,
        q: str | None,
        sort: tuple[str, bool] | None,
        limit: int,
        offset: int,
    ) -> tuple[list[ProductEntity], int]:
        """Returns one page of products and the total count."""

    @abstractmethod
    def references(self, records: list[ProductEntity]) -> References:
        """Labels of the records these refer to, one query per reference (Story 10.0b)."""
