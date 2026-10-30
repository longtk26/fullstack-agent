import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from src.modules.shared.domain.entities import SpecDraftEntity


class ISpecDraftRepository(ABC):
    @abstractmethod
    def create(self, draft: SpecDraftEntity) -> SpecDraftEntity:
        pass

    @abstractmethod
    def find_by_id(self, draft_id: uuid.UUID) -> SpecDraftEntity | None:
        pass

    @abstractmethod
    def update(self, draft_id: uuid.UUID, **fields: Any) -> SpecDraftEntity:
        pass

    @abstractmethod
    def claim(self, draft_id: uuid.UUID, worker_id: str) -> SpecDraftEntity | None:
        """PENDING → RUNNING for this worker; None when another worker has it or it is finished."""

    @abstractmethod
    def find_stale_running(self, updated_before: datetime) -> list[SpecDraftEntity]:
        pass

    @abstractmethod
    def list_created_between(
        self, owner_id: uuid.UUID | None, start: datetime, end: datetime, limit: int
    ) -> list[SpecDraftEntity]:
        pass
