import uuid
from abc import ABC, abstractmethod
from typing import Any

from src.modules.shared.domain.entities import TaskEntity


class ITaskRepository(ABC):
    @abstractmethod
    def create(self, task: TaskEntity) -> TaskEntity:
        pass

    @abstractmethod
    def find_by_id(self, task_id: uuid.UUID) -> TaskEntity | None:
        pass

    @abstractmethod
    def list(
        self, filters: dict[str, Any], sort: tuple[str, bool] | None, limit: int, offset: int
    ) -> tuple[list[TaskEntity], int]:
        """Returns one page and the total count; `filters` are equality matches on entity attributes."""

    @abstractmethod
    def update(self, task: TaskEntity) -> TaskEntity:
        pass

    @abstractmethod
    def delete(self, task_id: uuid.UUID) -> None:
        pass
