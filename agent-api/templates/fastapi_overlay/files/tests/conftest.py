"""Test harness (generator-owned): a real PostgreSQL, migrated once, emptied before every test.

TEST_DB_URL (or DB_URL) must point at a disposable database: every table is truncated between tests.
"""

import os
from collections.abc import Iterator

import pytest

os.environ["DB_URL"] = os.environ.get("TEST_DB_URL") or os.environ["DB_URL"]
os.environ.setdefault("RATE_LIMIT_DEFAULT", "100000/minute")

from alembic import command  # noqa: E402
from alembic.config import Config as AlembicConfig  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

import src.modules  # noqa: E402, F401
from src.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _migrated_database() -> Iterator[None]:
    command.upgrade(AlembicConfig("alembic.ini"), "head")
    yield


@pytest.fixture(autouse=True)
def _empty_tables() -> Iterator[None]:
    tables = [table.name for table in SQLModel.metadata.sorted_tables]
    if tables:
        engine = create_engine(os.environ["DB_URL"])
        with engine.begin() as connection:
            quoted = ", ".join(f'"{name}"' for name in tables)
            connection.execute(text(f"TRUNCATE {quoted} RESTART IDENTITY CASCADE"))
        engine.dispose()
    yield


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    # One client for the session: the lifespan registers the routers when the app starts.
    with TestClient(app) as test_client:
        yield test_client
