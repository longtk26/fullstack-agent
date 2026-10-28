import uuid
from typing import Annotated

from fastapi import Depends

from src.modules.products.ports.output import IProductRepoDep
from src.modules.products.presenter.dtos import ListProductsResponseDto, ProductResponseDto

SORT_FIELDS = {"name": "name", "price": "price", "createdAt": "created_at"}


class ListProductsUsecase:
    def __init__(self, product_repo: IProductRepoDep):
        self.product_repo = product_repo

    async def execute(
        self,
        category_id: uuid.UUID | None,
        q: str | None,
        sort: str | None,
        limit: int,
        offset: int,
    ) -> ListProductsResponseDto:
        order = (SORT_FIELDS[sort.lstrip("-")], sort.startswith("-")) if sort else None
        products, total = self.product_repo.list(category_id, q, order, limit, offset)
        return ListProductsResponseDto(
            items=[ProductResponseDto.from_entity(product) for product in products],
            total=total,
            limit=limit,
            offset=offset,
        )


ListProductsUsecaseDep = Annotated[ListProductsUsecase, Depends(ListProductsUsecase)]
