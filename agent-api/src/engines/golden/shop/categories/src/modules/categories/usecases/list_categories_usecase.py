from typing import Annotated

from fastapi import Depends

from src.modules.categories.ports.output import ICategoryRepoDep
from src.modules.categories.presenter.dtos import CategoryResponseDto, ListCategoriesResponseDto

SORT_FIELDS = {"name": "name"}


class ListCategoriesUsecase:
    def __init__(self, category_repo: ICategoryRepoDep):
        self.category_repo = category_repo

    async def execute(self, sort: str | None, limit: int, offset: int) -> ListCategoriesResponseDto:
        order = (SORT_FIELDS[sort.lstrip("-")], sort.startswith("-")) if sort else None
        categories, total = self.category_repo.list(order, limit, offset)
        return ListCategoriesResponseDto(
            items=[CategoryResponseDto.from_entity(category) for category in categories],
            total=total,
            limit=limit,
            offset=offset,
        )


ListCategoriesUsecaseDep = Annotated[ListCategoriesUsecase, Depends(ListCategoriesUsecase)]
