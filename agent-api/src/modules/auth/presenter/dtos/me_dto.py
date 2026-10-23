from datetime import datetime

from src.libs.dtos import CamelModel
from src.modules.shared.domain.entities import UserEntity
from src.modules.shared.domain.enums import UserRole


class MeResponseDto(CamelModel):
    id: str
    email: str
    role: UserRole
    created_at: datetime | None

    @classmethod
    def from_entity(cls, user: UserEntity) -> "MeResponseDto":
        return cls(id=str(user.id), email=user.email, role=user.role, created_at=user.created_at)
