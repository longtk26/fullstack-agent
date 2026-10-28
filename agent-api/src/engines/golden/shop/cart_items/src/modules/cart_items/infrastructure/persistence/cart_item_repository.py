import uuid
from typing import Annotated

from fastapi import Depends
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, func, select

from src.libs.database.session import SessionDep
from src.libs.exceptions import BadRequestException, ConflictException, ErrorCode
from src.modules.cart_items.ports.output.cart_item_repository import ICartItemRepository
from src.modules.shared.domain.entities import CartItemEntity
from src.modules.shared.infrastructure.models import CartItemModel

FOREIGN_KEY_VIOLATION = "23503"


class CartItemRepository(ICartItemRepository):
    def __init__(self, session: SessionDep):
        self.session = session

    def create(self, cart_item: CartItemEntity) -> CartItemEntity:
        model = self.__to_model(cart_item)
        self.session.add(model)
        self.__flush()
        return self.__to_entity(model)

    def find_by_id(self, cart_item_id: uuid.UUID) -> CartItemEntity | None:
        model = self.session.get(CartItemModel, cart_item_id)
        return self.__to_entity(model) if model else None

    def list(self, sort: tuple[str, bool] | None, limit: int, offset: int) -> tuple[list[CartItemEntity], int]:
        query = select(CartItemModel)
        total = self.session.exec(select(func.count()).select_from(query.subquery())).one()
        if sort:
            column = col(getattr(CartItemModel, sort[0]))
            query = query.order_by(column.desc() if sort[1] else column.asc(), col(CartItemModel.id))
        else:
            query = query.order_by(col(CartItemModel.created_at), col(CartItemModel.id))
        models = self.session.exec(query.offset(offset).limit(limit)).all()
        return [self.__to_entity(model) for model in models], total

    def update(self, cart_item: CartItemEntity) -> CartItemEntity:
        model = self.session.get(CartItemModel, cart_item.id)
        for key, value in cart_item.model_dump(exclude={"id", "created_at"}).items():
            setattr(model, key, value)
        self.__flush()
        return self.__to_entity(model)

    def delete(self, cart_item_id: uuid.UUID) -> None:
        model = self.session.get(CartItemModel, cart_item_id)
        if model is not None:
            self.session.delete(model)
            self.session.flush()

    def __flush(self) -> None:
        try:
            self.session.flush()
        except IntegrityError as exc:
            if getattr(exc.orig, "pgcode", None) == FOREIGN_KEY_VIOLATION:
                message = "The referenced product does not exist"
                raise BadRequestException(message, ErrorCode.REFERENCE_NOT_FOUND) from exc
            raise ConflictException("The cart item conflicts with an existing record") from exc

    def __to_entity(self, model: CartItemModel) -> CartItemEntity:
        return CartItemEntity.model_validate(model.model_dump())

    def __to_model(self, entity: CartItemEntity) -> CartItemModel:
        return CartItemModel(**entity.model_dump(exclude_none=True))


ICartItemRepoDep = Annotated[ICartItemRepository, Depends(CartItemRepository)]
