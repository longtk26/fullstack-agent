from abc import ABC, abstractmethod

from src.modules.shared.domain.entities import CategoryEntity


class ICategoryRepository(ABC):
    @abstractmethod
    def list(self, sort: tuple[str, bool] | None, limit: int, offset: int) -> tuple[list[CategoryEntity], int]:
        """Returns one page of categories and the total count."""
