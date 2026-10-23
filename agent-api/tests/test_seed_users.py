import pytest
from sqlmodel import Session

from src.libs.database import db_session_manager
from src.libs.security import verify_password
from src.modules.auth.infrastructure.persistence import UserRepository
from src.modules.auth.usecases import SeedUsersUsecase, parse_seed_users
from src.modules.shared.domain.enums import UserRole


def test_parse_seed_users_defaults_role_and_lowercases_email():
    assert parse_seed_users(" A@x.io:pw , b@x.io:pw2:admin ,") == [
        ("a@x.io", "pw", UserRole.USER),
        ("b@x.io", "pw2", UserRole.ADMIN),
    ]


@pytest.mark.parametrize("raw", ["missing-password", ":pw", "a@x.io:pw:superuser"])
def test_parse_seed_users_rejects_malformed_entries(raw):
    with pytest.raises(ValueError):
        parse_seed_users(raw)


async def _seed(raw: str) -> None:
    with Session(db_session_manager.engine) as session:
        await SeedUsersUsecase(UserRepository(session)).execute(raw)


def _find(email: str):
    with Session(db_session_manager.engine) as session:
        return UserRepository(session).find_by_email(email)


def test_reseeding_updates_password_and_role_without_duplicating(client):
    import asyncio

    asyncio.run(_seed("seeded@test.local:first"))
    first = _find("seeded@test.local")
    asyncio.run(_seed("seeded@test.local:second:ADMIN"))
    second = _find("seeded@test.local")

    assert second.id == first.id
    assert second.role == UserRole.ADMIN
    assert verify_password("second", second.password_hash)
