from typing import Annotated

from fastapi import Depends

from src.configs import get_logger
from src.libs.decorators.transactional_decorator import Transactional
from src.modules.cart_items.ports.output import ICartItemRepoDep
from src.modules.cart_items.presenter.dtos import CartItemResponseDto, CreateCartItemRequestDto

logger = get_logger(__name__)


class CreateCartItemUsecase:
    def __init__(self, cart_item_repo: ICartItemRepoDep):
        self.cart_item_repo = cart_item_repo

    @Transactional
    async def execute(self, dto: CreateCartItemRequestDto) -> CartItemResponseDto:
        cart_item = self.cart_item_repo.create(dto.to_entity())
        logger.info("cart_item created", extra={"cart_item_id": str(cart_item.id)})
        return CartItemResponseDto.from_entity(cart_item)


CreateCartItemUsecaseDep = Annotated[CreateCartItemUsecase, Depends(CreateCartItemUsecase)]
