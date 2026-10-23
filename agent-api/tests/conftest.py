import os

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
