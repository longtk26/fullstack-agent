from alembic.config import Config

from alembic import command


def test_models_and_migrations_have_no_drift(migrated_database):
    command.check(Config("alembic.ini"))


def test_downgrade_to_base_and_back(migrated_database):
    cfg = Config("alembic.ini")

    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
