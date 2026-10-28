import uuid

from fastapi import APIRouter, Query, status

from src.modules.cart_items.presenter.dtos import (
    CartItemResponseDto,
    CreateCartItemRequestDto,
    ListCartItemsResponseDto,
    UpdateCartItemRequestDto,
)
from src.modules.cart_items.usecases import (
    CreateCartItemUsecaseDep,
    DeleteCartItemUsecaseDep,
    ListCartItemsUsecaseDep,
    UpdateCartItemUsecaseDep,
)

cart_item_router = APIRouter(tags=["cart_items"])

ERROR = {"description": "Error envelope: {error: {code, message, details}}"}


@cart_item_router.get(
    "/cart-items",
    operation_id="cartItem.list",
    response_model=ListCartItemsResponseDto,
    responses={422: ERROR},
)
async def list_cart_items(
    usecase: ListCartItemsUsecaseDep,
    sort: str | None = Query(default=None, pattern=r"^-?(createdAt)$"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ListCartItemsResponseDto:
    return await usecase.execute(sort, limit, offset)


@cart_item_router.post(
    "/cart-items",
    operation_id="cartItem.create",
    response_model=CartItemResponseDto,
    status_code=status.HTTP_201_CREATED,
    responses={400: ERROR, 422: ERROR},
)
async def create_cart_item(body: CreateCartItemRequestDto, usecase: CreateCartItemUsecaseDep) -> CartItemResponseDto:
    return await usecase.execute(body)


@cart_item_router.patch(
    "/cart-items/{id}",
    operation_id="cartItem.update",
    response_model=CartItemResponseDto,
    responses={400: ERROR, 404: ERROR, 422: ERROR},
)
async def update_cart_item(
    id: uuid.UUID, body: UpdateCartItemRequestDto, usecase: UpdateCartItemUsecaseDep
) -> CartItemResponseDto:
    return await usecase.execute(id, body)


@cart_item_router.delete(
    "/cart-items/{id}",
    operation_id="cartItem.delete",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: ERROR},
)
async def delete_cart_item(id: uuid.UUID, usecase: DeleteCartItemUsecaseDep) -> None:
    await usecase.execute(id)
