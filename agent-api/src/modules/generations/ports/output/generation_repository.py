import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from src.modules.shared.domain.entities import GenerationEntity
from src.modules.shared.domain.enums import GenerationStatus


class IGenerationRepository(ABC):
    @abstractmethod
    def create(self, generation: GenerationEntity) -> GenerationEntity:
        pass

    @abstractmethod
    def find_by_id(self, generation_id: str) -> GenerationEntity | None:
        pass

    @abstractmethod
    def update(self, generation_id: str, **fields: Any) -> GenerationEntity:
        pass

    @abstractmethod
    def list_page(
        self,
        owner_id: uuid.UUID | None,
        status: GenerationStatus | None,
        before: tuple[datetime, str] | None,
        limit: int,
    ) -> list[GenerationEntity]:
        """Newest first; `before` is the (created_at, id) of the last row of the previous page."""

    @abstractmethod
    def find_stale_active(self, heartbeat_before: datetime) -> list[GenerationEntity]:
        pass

    @abstractmethod
    def find_pending_created_before(self, created_before: datetime) -> list[GenerationEntity]:
        pass

    @abstractmethod
    def find_finished_before(self, finished_before: datetime) -> list[str]:
        pass

    @abstractmethod
    def list_created_between(
        self, owner_id: uuid.UUID | None, start: datetime, end: datetime, limit: int
    ) -> list[GenerationEntity]:
        """Newest first, for usage reports (Story 9.10)."""
