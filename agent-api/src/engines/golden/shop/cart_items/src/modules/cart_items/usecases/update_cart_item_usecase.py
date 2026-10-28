import uuid
from typing import Annotated

from fastapi import Depends

from src.configs import get_logger
from src.libs.decorators.transactional_decorator import Transactional
from src.libs.exceptions import NotFoundException
from src.modules.cart_items.ports.output import ICartItemRepoDep
from src.modules.cart_items.presenter.dtos import CartItemResponseDto, UpdateCartItemRequestDto

logger = get_logger(__name__)


class UpdateCartItemUsecase:
    def __init__(self, cart_item_repo: ICartItemRepoDep):
        self.cart_item_repo = cart_item_repo

    @Transactional
    async def execute(self, cart_item_id: uuid.UUID, dto: UpdateCartItemRequestDto) -> CartItemResponseDto:
        current = self.cart_item_repo.find_by_id(cart_item_id)
        if current is None:
            raise NotFoundException("Cart item not found", details={"id": str(cart_item_id)})
        cart_item = self.cart_item_repo.update(dto.to_entity(current))
        logger.info("cart_item updated", extra={"cart_item_id": str(cart_item_id)})
        return CartItemResponseDto.from_entity(cart_item)


UpdateCartItemUsecaseDep = Annotated[UpdateCartItemUsecase, Depends(UpdateCartItemUsecase)]
