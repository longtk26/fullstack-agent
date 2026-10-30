import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from src.modules.shared.domain.entities import UploadEntity


class IUploadRepository(ABC):
    @abstractmethod
    def create(self, upload: UploadEntity) -> UploadEntity:
        pass

    @abstractmethod
    def find(self, upload_id: str) -> UploadEntity | None:
        pass

    @abstractmethod
    def find_by_sha256(self, owner_id: uuid.UUID, sha256: str) -> UploadEntity | None:
        pass

    @abstractmethod
    def list_for_owner(self, owner_id: uuid.UUID) -> list[UploadEntity]:
        pass

    @abstractmethod
    def total_bytes(self, owner_id: uuid.UUID) -> int:
        pass

    @abstractmethod
    def delete(self, upload_id: str) -> None:
        pass

    @abstractmethod
    def unreferenced_before(self, created_before: datetime) -> list[UploadEntity]:
        """Uploads older than the cut-off that no saved FrontendSpec uses (`upload:<id>`)."""
