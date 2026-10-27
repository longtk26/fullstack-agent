import uuid
from datetime import datetime

from sqlalchemy import Text
from sqlmodel import Field, SQLModel

from ._columns import TZDateTime


class SandboxExecModel(SQLModel, table=True):
    """One command run in the job's sandbox, for `sandbox:*` trace spans and sandbox time (Story 8.3)."""

    __tablename__ = "sandbox_execs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    generation_id: str = Field(foreign_key="generations.id", ondelete="CASCADE", index=True, max_length=32)
    node_run_id: uuid.UUID | None = Field(default=None, foreign_key="node_runs.id", ondelete="SET NULL")
    name: str = Field(max_length=64)
    command: str = Field(sa_type=Text)
    status: str = Field(max_length=16)
    exit_code: int | None = None
    started_at: datetime = Field(sa_type=TZDateTime)
    duration_ms: int = 0
