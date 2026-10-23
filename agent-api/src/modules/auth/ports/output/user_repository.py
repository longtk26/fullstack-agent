import uuid
from abc import ABC, abstractmethod

from src.modules.shared.domain.entities import UserEntity


class IUserRepository(ABC):
    @abstractmethod
    def create(self, user: UserEntity) -> UserEntity:
        pass

    @abstractmethod
    def update(self, user: UserEntity) -> UserEntity:
        pass

    @abstractmethod
    def find_by_id(self, user_id: uuid.UUID) -> UserEntity | None:
        pass

    @abstractmethod
    def find_by_email(self, email: str) -> UserEntity | None:
        pass
