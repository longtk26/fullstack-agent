from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from sqlalchemy.engine import make_url

from src.configs import config


def checkpoint_conninfo(db_url: str | None = None) -> str:
    url = make_url(db_url or config.db_url).set(drivername="postgresql")
    return url.render_as_string(hide_password=False)


@asynccontextmanager
async def postgres_checkpointer(db_url: str | None = None, schema: str | None = None):
    """LangGraph checkpoints in their own schema, so Alembic (which owns `public`) never sees their tables."""
    conninfo = checkpoint_conninfo(db_url)
    schema = schema or config.checkpoint_schema
    async with await AsyncConnection.connect(conninfo, autocommit=True) as conn:
        await conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
    kwargs = {
        "autocommit": True,
        "prepare_threshold": 0,
        "row_factory": dict_row,
        "options": f"-c search_path={schema}",
        "connect_timeout": 5,
        "keepalives": 1,
    }
    async with AsyncConnectionPool(
        conninfo,
        kwargs=kwargs,
        min_size=1,
        max_size=5,
        open=False,
        check=AsyncConnectionPool.check_connection,  # drops connections broken by a Postgres restart
    ) as pool:
        saver = AsyncPostgresSaver(pool)
        await saver.setup()
        yield saver
