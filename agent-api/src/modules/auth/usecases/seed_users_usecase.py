from src.configs import get_logger
from src.libs.decorators.transactional_decorator import Transactional
from src.libs.security import hash_password, verify_password
from src.modules.auth.ports.output import IUserRepository
from src.modules.shared.domain.entities import UserEntity
from src.modules.shared.domain.enums import UserRole

logger = get_logger(__name__)


def parse_seed_users(raw: str) -> list[tuple[str, str, UserRole]]:
    """`email:password[:role]` entries separated by commas."""
    seeds = []
    for entry in filter(None, (part.strip() for part in raw.split(","))):
        email, _, rest = entry.partition(":")
        password, _, role = rest.partition(":")
        if not email or not password:
            raise ValueError(f"Invalid SEED_USERS entry for '{email or entry}': expected email:password[:role]")
        seeds.append((email.lower(), password, UserRole(role.upper()) if role else UserRole.USER))
    return seeds


class SeedUsersUsecase:
    def __init__(self, user_repo: IUserRepository):
        self.user_repo = user_repo

    @Transactional
    async def execute(self, raw_seed_users: str) -> int:
        seeds = parse_seed_users(raw_seed_users)
        for email, password, role in seeds:
            existing = self.user_repo.find_by_email(email)
            if existing is None:
                self.user_repo.create(UserEntity(email=email, password_hash=hash_password(password), role=role))
            elif existing.role != role or not verify_password(password, existing.password_hash):
                existing.role = role
                existing.password_hash = hash_password(password)
                self.user_repo.update(existing)
        logger.info("seeded users", extra={"count": len(seeds)})
        return len(seeds)
