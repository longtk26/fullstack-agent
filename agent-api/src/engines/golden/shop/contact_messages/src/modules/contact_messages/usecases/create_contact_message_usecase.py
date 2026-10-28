from typing import Annotated

from fastapi import Depends

from src.configs import get_logger
from src.libs.decorators.transactional_decorator import Transactional
from src.modules.contact_messages.ports.output import IContactMessageRepoDep
from src.modules.contact_messages.presenter.dtos import (
    ContactMessageResponseDto,
    CreateContactMessageRequestDto,
)

logger = get_logger(__name__)


class CreateContactMessageUsecase:
    def __init__(self, contact_message_repo: IContactMessageRepoDep):
        self.contact_message_repo = contact_message_repo

    @Transactional
    async def execute(self, dto: CreateContactMessageRequestDto) -> ContactMessageResponseDto:
        message = self.contact_message_repo.create(dto.to_entity())
        logger.info("contact_message created", extra={"contact_message_id": str(message.id)})
        return ContactMessageResponseDto.from_entity(message)


CreateContactMessageUsecaseDep = Annotated[CreateContactMessageUsecase, Depends(CreateContactMessageUsecase)]
