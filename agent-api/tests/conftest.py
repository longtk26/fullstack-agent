import os
from pathlib import Path

import psycopg
import pytest
from sqlalchemy.engine import make_url

_base_url = make_url(os.environ.get("DB_URL", "postgresql+psycopg://bga:bga@localhost:5442/agent"))
TEST_DB_URL = _base_url.set(database=f"{_base_url.database}_test")

os.environ["DB_URL"] = TEST_DB_URL.render_as_string(hide_password=False)
os.environ["JWT_SECRET"] = "test-secret-" + "x" * 32
os.environ["SEED_USERS"] = "admin@test.local:adminpass:ADMIN,user@test.local:userpass,other@test.local:otherpass"
os.environ["RATE_LIMIT_LOGIN"] = "5/minute"
os.environ["RATE_LIMIT_STORAGE_URI"] = "memory://"
os.environ["REDIS_URL"] = os.environ.get("REDIS_URL", "redis://localhost:6389/0").rsplit("/", 1)[0] + "/15"
os.environ["ENGINE_SKILLS_DIR"] = str(Path(__file__).parents[2] / ".agents" / "skills")
os.environ.setdefault("TEMPLATE_DIR", str(Path(__file__).parents[2] / ".data" / "fastapi-template"))
# Pin settings a developer's .env may change (the Makefile exports .env into the test process).
os.environ["DEFAULT_ENGINE"] = "claude_code"
os.environ["ANTIGRAVITY_AUTH"] = "gemini_api_key"
os.environ["SANDBOX_ENABLED"] = "false"  # sandbox tests opt in with BGA_SANDBOX_TESTS=1


def _recreate_test_database() -> None:
    admin_url = TEST_DB_URL.set(drivername="postgresql", database="postgres").render_as_string(hide_password=False)
    with psycopg.connect(admin_url, autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB_URL.database}" WITH (FORCE)')
        conn.execute(f'CREATE DATABASE "{TEST_DB_URL.database}"')


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    from alembic.config import Config

    from alembic import command

    _recreate_test_database()
    command.upgrade(Config("alembic.ini"), "head")
    yield


@pytest.fixture(scope="session")
def client(migrated_database):
    from fastapi.testclient import TestClient

    from src.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_rate_limits():
    from src.libs.rate_limit import limiter

    limiter.reset()
    yield


@pytest.fixture
def login(client):
    def _login(email: str, password: str) -> str:
        response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200, response.text
        return response.json()["accessToken"]

    return _login


@pytest.fixture
def user_headers(login):
    return {"Authorization": f"Bearer {login('user@test.local', 'userpass')}"}


@pytest.fixture
def clean_redis():
    import asyncio

    from redis.asyncio import Redis

    from src.configs import config

    async def flush():
        client = Redis.from_url(config.redis_url)
        await client.flushdb()
        await client.aclose()

    asyncio.run(flush())
    yield
