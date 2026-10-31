import uuid

from fastapi import APIRouter, Query

from src.modules.decks.presenter.dtos import (
    CreateDeckRequestDto,
    DeckResponseDto,
    ListDecksResponseDto,
    StatsDeckResponseDto,
    UpdateDeckRequestDto,
)
from src.modules.decks.usecases import (
    CreateDeckUsecaseDep,
    DeleteDeckUsecaseDep,
    GetDeckUsecaseDep,
    ListDecksUsecaseDep,
    StatsDeckUsecaseDep,
    UpdateDeckUsecaseDep,
)

deck_router = APIRouter(tags=["decks"])

ERROR = {"description": "Error envelope: {error: {code, message, details}}"}


@deck_router.get("/decks", operation_id="deck.list", response_model=ListDecksResponseDto, responses={422: ERROR})
async def list_decks(
    usecase: ListDecksUsecaseDep,
    sort: str | None = Query(default=None, pattern=r"^-?(name|createdAt)$"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ListDecksResponseDto:
    return await usecase.execute(sort, limit, offset)


@deck_router.get("/decks/{id}", operation_id="deck.get", response_model=DeckResponseDto, responses={404: ERROR})
async def get_deck(id: uuid.UUID, usecase: GetDeckUsecaseDep) -> DeckResponseDto:
    return await usecase.execute(id)


@deck_router.get(
    "/decks/{id}/stats",
    operation_id="deck.stats",
    response_model=StatsDeckResponseDto,
    responses={404: ERROR},
)
async def stats_deck(id: uuid.UUID, usecase: StatsDeckUsecaseDep) -> StatsDeckResponseDto:
    return await usecase.execute(id)


@deck_router.post(
    "/decks",
    operation_id="deck.create",
    response_model=DeckResponseDto,
    status_code=201,
    responses={400: ERROR, 422: ERROR},
)
async def create_deck(body: CreateDeckRequestDto, usecase: CreateDeckUsecaseDep) -> DeckResponseDto:
    return await usecase.execute(body)


@deck_router.patch(
    "/decks/{id}",
    operation_id="deck.update",
    response_model=DeckResponseDto,
    responses={400: ERROR, 404: ERROR, 422: ERROR},
)
async def update_deck(id: uuid.UUID, body: UpdateDeckRequestDto, usecase: UpdateDeckUsecaseDep) -> DeckResponseDto:
    return await usecase.execute(id, body)


@deck_router.delete("/decks/{id}", operation_id="deck.delete", status_code=204, responses={404: ERROR})
async def delete_deck(id: uuid.UUID, usecase: DeleteDeckUsecaseDep) -> None:
    await usecase.execute(id)
