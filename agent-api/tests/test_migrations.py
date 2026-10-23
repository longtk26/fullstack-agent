import asyncio
import os

from alembic.config import Config

from alembic import command
from src.modules.auth.bootstrap import seed_users


def test_models_and_migrations_have_no_drift(migrated_database):
    command.check(Config("alembic.ini"))


def test_downgrade_to_base_and_back(migrated_database):
    cfg = Config("alembic.ini")

    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")

    # The downgrade dropped every table; restore the seeded users the rest of the session relies on.
    asyncio.run(seed_users(os.environ["SEED_USERS"]))
