from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends
from sqlalchemy import or_
from sqlmodel import col, func, select

from src.libs.database.session import SessionDep
from src.modules.products.ports.output.product_repository import IProductRepository
from src.modules.shared.domain.entities import ProductEntity
from src.modules.shared.infrastructure.models import CategoryModel, ProductModel
from src.modules.shared.presenter.summaries import References


class ProductRepository(IProductRepository):
    def __init__(self, session: SessionDep):
        self.session = session

    def find_by_id(self, product_id: uuid.UUID) -> ProductEntity | None:
        model = self.session.get(ProductModel, product_id)
        return self.__to_entity(model) if model else None

    def list(
        self,
        category_id: uuid.UUID | None,
        q: str | None,
        sort: tuple[str, bool] | None,
        limit: int,
        offset: int,
    ) -> tuple[list[ProductEntity], int]:
        query = select(ProductModel)
        if category_id is not None:
            query = query.where(col(ProductModel.category_id) == category_id)
        if q:
            pattern = f"%{q}%"
            query = query.where(
                or_(
                    col(ProductModel.name).ilike(pattern),
                    col(ProductModel.description).ilike(pattern),
                )
            )
        total = self.session.exec(select(func.count()).select_from(query.subquery())).one()
        if sort:
            column = col(getattr(ProductModel, sort[0]))
            query = query.order_by(column.desc() if sort[1] else column.asc(), col(ProductModel.id))
        else:
            query = query.order_by(col(ProductModel.created_at), col(ProductModel.id))
        models = self.session.exec(query.offset(offset).limit(limit)).all()
        return [self.__to_entity(model) for model in models], total

    def references(self, records: list[ProductEntity]) -> References:
        found: References = {}
        category_ids = {record.category_id for record in records if record.category_id is not None}
        found["category"] = {}
        if category_ids:
            query = select(col(CategoryModel.id), col(CategoryModel.name)).where(
                col(CategoryModel.id).in_(category_ids)
            )
            found["category"] = {
                key: None if label is None else str(label) for key, label in self.session.exec(query).all()
            }
        return found

    def __to_entity(self, model: ProductModel) -> ProductEntity:
        return ProductEntity.model_validate(model.model_dump())


IProductRepoDep = Annotated[IProductRepository, Depends(ProductRepository)]
