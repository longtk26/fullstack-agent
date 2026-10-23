import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from ._columns import Json, TZDateTime, utcnow


class CliInvocationModel(SQLModel, table=True):
    __tablename__ = "cli_invocations"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    generation_id: str = Field(foreign_key="generations.id", ondelete="CASCADE", index=True, max_length=32)
    node_run_id: uuid.UUID | None = Field(default=None, foreign_key="node_runs.id", ondelete="SET NULL")
    engine: str = Field(max_length=32)
    purpose: str = Field(max_length=64)
    argv_redacted: list[str] = Field(default_factory=list, sa_type=Json)
    exit_code: int | None = None
    status: str = Field(max_length=32)
    duration_ms: int | None = None
    turns: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    stdout_ref: str | None = None
    stderr_ref: str | None = None
    created_at: datetime = Field(default_factory=utcnow, sa_type=TZDateTime)
