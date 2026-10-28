from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from .cart_item_response_dto import CartItemResponseDto


class ListCartItemsResponseDto(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: list[CartItemResponseDto]
    total: int
    limit: int
    offset: int
