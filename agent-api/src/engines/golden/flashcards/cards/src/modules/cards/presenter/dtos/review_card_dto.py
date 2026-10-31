import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class ReviewCardRequestDto(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rating: Literal["again", "hard", "good", "easy"]

    def to_entity(self, card_id: uuid.UUID | None = None) -> Any:
        return self
