from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from .task_response_dto import TaskResponseDto


class ListTasksResponseDto(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: list[TaskResponseDto]
    total: int
    limit: int
    offset: int
