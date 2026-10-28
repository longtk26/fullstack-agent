from typing import Annotated

from fastapi import Depends
from sqlmodel import col, func, select

from src.libs.database.session import SessionDep
from src.modules.categories.ports.output.category_repository import ICategoryRepository
from src.modules.shared.domain.entities import CategoryEntity
from src.modules.shared.infrastructure.models import CategoryModel


class CategoryRepository(ICategoryRepository):
    def __init__(self, session: SessionDep):
        self.session = session

    def list(self, sort: tuple[str, bool] | None, limit: int, offset: int) -> tuple[list[CategoryEntity], int]:
        query = select(CategoryModel)
        total = self.session.exec(select(func.count()).select_from(query.subquery())).one()
        if sort:
            column = col(getattr(CategoryModel, sort[0]))
            query = query.order_by(column.desc() if sort[1] else column.asc(), col(CategoryModel.id))
        else:
            query = query.order_by(col(CategoryModel.name), col(CategoryModel.id))
        models = self.session.exec(query.offset(offset).limit(limit)).all()
        return [self.__to_entity(model) for model in models], total

    def __to_entity(self, model: CategoryModel) -> CategoryEntity:
        return CategoryEntity.model_validate(model.model_dump())


ICategoryRepoDep = Annotated[ICategoryRepository, Depends(CategoryRepository)]
