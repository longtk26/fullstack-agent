import uuid
from typing import Annotated

from fastapi import Depends
from sqlmodel import select

from src.libs.database.session import SessionDep
from src.modules.auth.ports.output import IUserRepository
from src.modules.shared.domain.entities import UserEntity
from src.modules.shared.infrastructure.models import UserModel


class UserRepository(IUserRepository):
    def __init__(self, session: SessionDep):
        self.session = session

    def create(self, user: UserEntity) -> UserEntity:
        model = self.__to_model(user)
        self.session.add(model)
        self.session.flush()
        return self.__to_entity(model)

    def update(self, user: UserEntity) -> UserEntity:
        model = self.session.get(UserModel, user.id)
        model.email = user.email
        model.password_hash = user.password_hash
        model.role = user.role
        self.session.flush()
        return self.__to_entity(model)

    def find_by_id(self, user_id: uuid.UUID) -> UserEntity | None:
        model = self.session.get(UserModel, user_id)
        return self.__to_entity(model) if model else None

    def find_by_email(self, email: str) -> UserEntity | None:
        model = self.session.exec(select(UserModel).where(UserModel.email == email.lower())).first()
        return self.__to_entity(model) if model else None

    def __to_entity(self, model: UserModel) -> UserEntity:
        return UserEntity(
            id=model.id,
            email=model.email,
            password_hash=model.password_hash,
            role=model.role,
            created_at=model.created_at,
        )

    def __to_model(self, entity: UserEntity) -> UserModel:
        model = UserModel(email=entity.email.lower(), password_hash=entity.password_hash, role=entity.role)
        if entity.id:
            model.id = entity.id
        return model


IUserRepoDep = Annotated[IUserRepository, Depends(UserRepository)]
