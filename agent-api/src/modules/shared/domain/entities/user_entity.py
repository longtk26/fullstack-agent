import uuid
from datetime import datetime

from pydantic import BaseModel

from src.modules.shared.domain.enums import UserRole


class UserEntity(BaseModel):
    id: uuid.UUID | None = None
    email: str
    password_hash: str
    role: UserRole = UserRole.USER
    created_at: datetime | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN
