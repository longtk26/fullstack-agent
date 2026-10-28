import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Text
from sqlmodel import Field, SQLModel


class ContactMessageModel(SQLModel, table=True):
    __tablename__ = "contact_messages"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=120)
    email: str = Field(max_length=254)
    message: str = Field(sa_type=Text)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), sa_type=DateTime(timezone=True))
