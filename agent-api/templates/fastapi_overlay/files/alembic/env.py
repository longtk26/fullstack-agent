from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlmodel import SQLModel

import src.modules  # noqa: F401  (imports every ORM model for autogenerate)
import src.modules.shared.infrastructure.models  # noqa: F401
from src.configs import config as app_config

config = context.config
config.set_main_option("sqlalchemy.url", app_config.db_url.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = SQLModel.metadata


def _needs_btree_gist() -> bool:
    """Story 10.10: an exclusion constraint that mixes `=` on a column with `&&` on a range needs btree_gist."""
    return any(
        isinstance(constraint, ExcludeConstraint)
        for table in target_metadata.tables.values()
        for constraint in table.constraints
    )


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            if _needs_btree_gist():
                connection.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS btree_gist")
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
