from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from .product_response_dto import ProductResponseDto


class ListProductsResponseDto(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: list[ProductResponseDto]
    total: int
    limit: int
    offset: int
