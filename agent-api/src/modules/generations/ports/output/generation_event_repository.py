from abc import ABC, abstractmethod

from src.modules.shared.domain.entities import GenerationEventEntity


class IGenerationEventRepository(ABC):
    @abstractmethod
    def append(self, event: GenerationEventEntity) -> GenerationEventEntity:
        pass

    @abstractmethod
    def list_after(self, generation_id: str, after_id: int, limit: int = 1000) -> list[GenerationEventEntity]:
        pass

    @abstractmethod
    def count(self, generation_id: str) -> int:
        pass
