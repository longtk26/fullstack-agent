import uuid

from fastapi import APIRouter, Query

from src.modules.cards.presenter.dtos import (
    CardResponseDto,
    CreateCardRequestDto,
    ListCardsResponseDto,
    ReviewCardRequestDto,
    UpdateCardRequestDto,
)
from src.modules.cards.usecases import (
    CreateCardUsecaseDep,
    DeleteCardUsecaseDep,
    GetCardUsecaseDep,
    ListCardsUsecaseDep,
    ListDueCardUsecaseDep,
    ReviewCardUsecaseDep,
    UpdateCardUsecaseDep,
)

card_router = APIRouter(tags=["cards"])

ERROR = {"description": "Error envelope: {error: {code, message, details}}"}


@card_router.get("/cards", operation_id="card.list", response_model=ListCardsResponseDto, responses={422: ERROR})
async def list_cards(
    usecase: ListCardsUsecaseDep,
    deck_id: uuid.UUID | None = Query(default=None, alias="deckId"),
    q: str | None = Query(default=None),
    sort: str | None = Query(default=None, pattern=r"^-?(dueDate|createdAt)$"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ListCardsResponseDto:
    return await usecase.execute(deck_id, q, sort, limit, offset)


@card_router.get("/cards/due", operation_id="card.listDue", response_model=list[CardResponseDto])
async def list_due_cards(
    usecase: ListDueCardUsecaseDep,
    deck_id: uuid.UUID | None = Query(default=None, alias="deckId"),
) -> list[CardResponseDto]:
    return await usecase.execute(deck_id)


@card_router.get("/cards/{id}", operation_id="card.get", response_model=CardResponseDto, responses={404: ERROR})
async def get_card(id: uuid.UUID, usecase: GetCardUsecaseDep) -> CardResponseDto:
    return await usecase.execute(id)


@card_router.post(
    "/cards",
    operation_id="card.create",
    response_model=CardResponseDto,
    status_code=201,
    responses={400: ERROR, 422: ERROR},
)
async def create_card(body: CreateCardRequestDto, usecase: CreateCardUsecaseDep) -> CardResponseDto:
    return await usecase.execute(body)


@card_router.post(
    "/cards/{id}/review",
    operation_id="card.review",
    response_model=CardResponseDto,
    responses={400: ERROR, 404: ERROR, 422: ERROR},
)
async def review_card(
    id: uuid.UUID,
    body: ReviewCardRequestDto,
    usecase: ReviewCardUsecaseDep,
) -> CardResponseDto:
    return await usecase.execute(id, body)


@card_router.patch(
    "/cards/{id}",
    operation_id="card.update",
    response_model=CardResponseDto,
    responses={400: ERROR, 404: ERROR, 422: ERROR},
)
async def update_card(id: uuid.UUID, body: UpdateCardRequestDto, usecase: UpdateCardUsecaseDep) -> CardResponseDto:
    return await usecase.execute(id, body)


@card_router.delete("/cards/{id}", operation_id="card.delete", status_code=204, responses={404: ERROR})
async def delete_card(id: uuid.UUID, usecase: DeleteCardUsecaseDep) -> None:
    await usecase.execute(id)
