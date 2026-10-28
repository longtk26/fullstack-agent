import uuid
from datetime import datetime

from pydantic import BaseModel


class ContactMessageEntity(BaseModel):
    id: uuid.UUID | None = None
    name: str
    email: str
    message: str
    created_at: datetime | None = None
