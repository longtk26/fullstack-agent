import uuid
from datetime import datetime

from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from src.modules.shared.domain.enums import UserRole

from ._columns import TZDateTime, utcnow


class UserModel(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(max_length=320, unique=True, index=True)
    password_hash: str
    role: UserRole = Field(default=UserRole.USER, sa_type=SAEnum(UserRole, name="user_role"))
    created_at: datetime = Field(default_factory=utcnow, sa_type=TZDateTime)
