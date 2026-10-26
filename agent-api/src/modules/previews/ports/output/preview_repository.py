import uuid
from abc import ABC, abstractmethod
from typing import Any

from src.modules.shared.domain.entities import PreviewEntity
from src.modules.shared.domain.enums import PreviewStatus


class IPreviewRepository(ABC):
    @abstractmethod
    def find(self, generation_id: str) -> PreviewEntity | None:
        pass

    @abstractmethod
    def upsert(self, generation_id: str, **fields: Any) -> PreviewEntity:
        pass

    @abstractmethod
    def delete(self, generation_id: str) -> None:
        pass

    @abstractmethod
    def list_for_owner(self, owner_id: uuid.UUID | None) -> list[PreviewEntity]:
        """All previews when owner_id is None (admins)."""

    @abstractmethod
    def list_by_status(self, statuses: tuple[PreviewStatus, ...]) -> list[PreviewEntity]:
        pass

    @abstractmethod
    def list_all(self) -> list[PreviewEntity]:
        pass
