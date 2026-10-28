from fastapi import APIRouter, Query

from src.modules.categories.presenter.dtos import ListCategoriesResponseDto
from src.modules.categories.usecases import ListCategoriesUsecaseDep

category_router = APIRouter(tags=["categories"])

ERROR = {"description": "Error envelope: {error: {code, message, details}}"}


@category_router.get(
    "/categories",
    operation_id="category.list",
    response_model=ListCategoriesResponseDto,
    responses={422: ERROR},
)
async def list_categories(
    usecase: ListCategoriesUsecaseDep,
    sort: str | None = Query(default=None, pattern=r"^-?(name)$"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ListCategoriesResponseDto:
    return await usecase.execute(sort, limit, offset)
