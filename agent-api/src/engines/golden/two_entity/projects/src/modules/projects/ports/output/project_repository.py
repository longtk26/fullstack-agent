import uuid
from abc import ABC, abstractmethod

from src.modules.shared.domain.entities import ProjectEntity


class IProjectRepository(ABC):
    @abstractmethod
    def create(self, project: ProjectEntity) -> ProjectEntity:
        pass

    @abstractmethod
    def find_by_id(self, project_id: uuid.UUID) -> ProjectEntity | None:
        pass

    @abstractmethod
    def list(self, sort: tuple[str, bool] | None, limit: int, offset: int) -> tuple[list[ProjectEntity], int]:
        """Returns one page and the total count; `sort` is (attribute, descending)."""

    @abstractmethod
    def update(self, project: ProjectEntity) -> ProjectEntity:
        pass

    @abstractmethod
    def delete(self, project_id: uuid.UUID) -> None:
        pass
