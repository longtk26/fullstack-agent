import uuid
from typing import Annotated

from fastapi import Depends

from src.configs import get_logger
from src.libs.decorators.transactional_decorator import Transactional
from src.libs.exceptions import NotFoundException
from src.modules.cart_items.ports.output import ICartItemRepoDep

logger = get_logger(__name__)


class DeleteCartItemUsecase:
    def __init__(self, cart_item_repo: ICartItemRepoDep):
        self.cart_item_repo = cart_item_repo

    @Transactional
    async def execute(self, cart_item_id: uuid.UUID) -> None:
        if self.cart_item_repo.find_by_id(cart_item_id) is None:
            raise NotFoundException("Cart item not found", details={"id": str(cart_item_id)})
        self.cart_item_repo.delete(cart_item_id)
        logger.info("cart_item deleted", extra={"cart_item_id": str(cart_item_id)})


DeleteCartItemUsecaseDep = Annotated[DeleteCartItemUsecase, Depends(DeleteCartItemUsecase)]
