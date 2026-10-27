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
    cost_source: str | None = Field(default=None, max_length=16)
    model: str | None = Field(default=None, max_length=128)
    cache_read_tokens: int | None = None
    cache_write_tokens: int | None = None
    thinking_tokens: int | None = None
    prompt_ref: str | None = Field(default=None, max_length=128)
    error_reason: str | None = Field(default=None, max_length=32)
    changed_files: list[str] = Field(default_factory=list, sa_type=Json)
    finished_at: datetime | None = Field(default=None, sa_type=TZDateTime)
    stdout_ref: str | None = None
    stderr_ref: str | None = None
    created_at: datetime = Field(default_factory=utcnow, sa_type=TZDateTime)
