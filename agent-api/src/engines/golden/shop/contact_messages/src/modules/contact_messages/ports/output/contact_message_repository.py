from abc import ABC, abstractmethod

from src.modules.shared.domain.entities import ContactMessageEntity


class IContactMessageRepository(ABC):
    @abstractmethod
    def create(self, message: ContactMessageEntity) -> ContactMessageEntity:
        pass
