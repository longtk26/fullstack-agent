from pydantic import BaseModel, ConfigDict


class StatsDeckResponseDto(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    total: int
    due_today: int
    learned: int
