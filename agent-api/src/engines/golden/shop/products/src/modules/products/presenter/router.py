import uuid

from fastapi import APIRouter, Query

from src.modules.products.presenter.dtos import ListProductsResponseDto, ProductResponseDto
from src.modules.products.usecases import GetProductUsecaseDep, ListProductsUsecaseDep

product_router = APIRouter(tags=["products"])

ERROR = {"description": "Error envelope: {error: {code, message, details}}"}


@product_router.get(
    "/products",
    operation_id="product.list",
    response_model=ListProductsResponseDto,
    responses={422: ERROR},
)
async def list_products(
    usecase: ListProductsUsecaseDep,
    category_id: uuid.UUID | None = Query(default=None, alias="categoryId"),
    q: str | None = Query(default=None),
    sort: str | None = Query(default=None, pattern=r"^-?(name|price|createdAt)$"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ListProductsResponseDto:
    return await usecase.execute(category_id, q, sort, limit, offset)


@product_router.get(
    "/products/{id}",
    operation_id="product.get",
    response_model=ProductResponseDto,
    responses={404: ERROR},
)
async def get_product(id: uuid.UUID, usecase: GetProductUsecaseDep) -> ProductResponseDto:
    return await usecase.execute(id)
