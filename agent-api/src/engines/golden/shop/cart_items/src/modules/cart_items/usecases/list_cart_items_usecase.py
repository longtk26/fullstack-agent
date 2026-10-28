from typing import Annotated

from fastapi import Depends

from src.modules.cart_items.ports.output import ICartItemRepoDep
from src.modules.cart_items.presenter.dtos import CartItemResponseDto, ListCartItemsResponseDto

SORT_FIELDS = {"createdAt": "created_at"}


class ListCartItemsUsecase:
    def __init__(self, cart_item_repo: ICartItemRepoDep):
        self.cart_item_repo = cart_item_repo

    async def execute(self, sort: str | None, limit: int, offset: int) -> ListCartItemsResponseDto:
        order = (SORT_FIELDS[sort.lstrip("-")], sort.startswith("-")) if sort else None
        cart_items, total = self.cart_item_repo.list(order, limit, offset)
        return ListCartItemsResponseDto(
            items=[CartItemResponseDto.from_entity(item) for item in cart_items],
            total=total,
            limit=limit,
            offset=offset,
        )


ListCartItemsUsecaseDep = Annotated[ListCartItemsUsecase, Depends(ListCartItemsUsecase)]
