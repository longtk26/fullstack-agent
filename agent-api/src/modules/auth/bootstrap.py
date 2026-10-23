from sqlmodel import Session

from src.libs.database import db_session_manager
from src.modules.auth.infrastructure.persistence import UserRepository
from src.modules.auth.usecases import SeedUsersUsecase


async def seed_users(raw_seed_users: str) -> int:
    with Session(db_session_manager.engine) as session:
        return await SeedUsersUsecase(UserRepository(session)).execute(raw_seed_users)
