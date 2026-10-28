import uuid

from pydantic import BaseModel


class CategoryEntity(BaseModel):
    id: uuid.UUID | None = None
    name: str
