from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class StatsDeckResponseDto(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    total: int
    due_today: int
    learned: int
