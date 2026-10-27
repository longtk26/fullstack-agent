import uuid
from abc import ABC, abstractmethod

from src.modules.shared.domain.entities import FrontendSpecEntity


class IFrontendSpecRepository(ABC):
    @abstractmethod
    def create(self, spec: FrontendSpecEntity) -> FrontendSpecEntity:
        pass

    @abstractmethod
    def find_by_id(self, spec_id: uuid.UUID) -> FrontendSpecEntity | None:
        pass

    @abstractmethod
    def find_by_ids(self, spec_ids: list[uuid.UUID]) -> dict[uuid.UUID, FrontendSpecEntity]:
        pass
