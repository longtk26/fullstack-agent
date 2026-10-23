import uuid
from abc import ABC, abstractmethod

from src.modules.shared.domain.entities import BackendSpecEntity


class IBackendSpecRepository(ABC):
    @abstractmethod
    def create(self, spec: BackendSpecEntity) -> BackendSpecEntity:
        pass

    @abstractmethod
    def find_by_id(self, spec_id: uuid.UUID) -> BackendSpecEntity | None:
        pass

    @abstractmethod
    def find_by_ids(self, spec_ids: list[uuid.UUID]) -> dict[uuid.UUID, BackendSpecEntity]:
        pass
