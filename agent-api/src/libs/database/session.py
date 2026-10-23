from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine

from src.configs import config


class DBSessionManager:
    def __init__(self):
        self.engine = self.create_db_engine(config.db_url)

    def create_db_engine(self, db_url: str):
        # Pre-ping + timeouts: a restarted Postgres must cost a reconnect, never a hung worker.
        return create_engine(
            db_url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 5, "keepalives": 1, "keepalives_idle": 30},
        )

    def create_db_and_tables(self):
        SQLModel.metadata.create_all(self.engine)

    def get_session(self):
        with Session(self.engine) as session:
            yield session


db_session_manager = DBSessionManager()

SessionDep = Annotated[Session, Depends(db_session_manager.get_session)]
