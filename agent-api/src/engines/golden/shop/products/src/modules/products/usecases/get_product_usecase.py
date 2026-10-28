import uuid
from typing import Annotated

from fastapi import Depends

from src.libs.exceptions import NotFoundException
from src.modules.products.ports.output import IProductRepoDep
from src.modules.products.presenter.dtos import ProductResponseDto


class GetProductUsecase:
    def __init__(self, product_repo: IProductRepoDep):
        self.product_repo = product_repo

    async def execute(self, product_id: uuid.UUID) -> ProductResponseDto:
        product = self.product_repo.find_by_id(product_id)
        if product is None:
            raise NotFoundException("Product not found", details={"id": str(product_id)})
        return ProductResponseDto.from_entity(product)


GetProductUsecaseDep = Annotated[GetProductUsecase, Depends(GetProductUsecase)]
