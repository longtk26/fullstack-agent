from typing import Annotated

from fastapi import Depends

from src.libs.database.session import SessionDep
from src.modules.contact_messages.ports.output.contact_message_repository import IContactMessageRepository
from src.modules.shared.domain.entities import ContactMessageEntity
from src.modules.shared.infrastructure.models import ContactMessageModel


class ContactMessageRepository(IContactMessageRepository):
    def __init__(self, session: SessionDep):
        self.session = session

    def create(self, message: ContactMessageEntity) -> ContactMessageEntity:
        model = self.__to_model(message)
        self.session.add(model)
        self.session.flush()
        return self.__to_entity(model)

    def __to_entity(self, model: ContactMessageModel) -> ContactMessageEntity:
        return ContactMessageEntity.model_validate(model.model_dump())

    def __to_model(self, entity: ContactMessageEntity) -> ContactMessageModel:
        return ContactMessageModel(**entity.model_dump(exclude_none=True))


IContactMessageRepoDep = Annotated[IContactMessageRepository, Depends(ContactMessageRepository)]
