from fastapi import APIRouter, status

from src.modules.contact_messages.presenter.dtos import (
    ContactMessageResponseDto,
    CreateContactMessageRequestDto,
)
from src.modules.contact_messages.usecases import CreateContactMessageUsecaseDep

contact_message_router = APIRouter(tags=["contact_messages"])

ERROR = {"description": "Error envelope: {error: {code, message, details}}"}


@contact_message_router.post(
    "/contact-messages",
    operation_id="contactMessage.create",
    response_model=ContactMessageResponseDto,
    status_code=status.HTTP_201_CREATED,
    responses={422: ERROR},
)
async def create_contact_message(
    body: CreateContactMessageRequestDto, usecase: CreateContactMessageUsecaseDep
) -> ContactMessageResponseDto:
    return await usecase.execute(body)
