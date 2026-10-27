import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from ._columns import Json, TZDateTime


class ModelCallModel(SQLModel, table=True):
    """One model request inside a CLI session (Story 8.4)."""

    __tablename__ = "model_calls"
    __table_args__ = (Index("ix_model_calls_generation_id_seq", "generation_id", "cli_invocation_id", "seq"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    generation_id: str = Field(foreign_key="generations.id", ondelete="CASCADE", max_length=32)
    cli_invocation_id: uuid.UUID = Field(foreign_key="cli_invocations.id", ondelete="CASCADE")
    node_run_id: uuid.UUID | None = Field(default=None, foreign_key="node_runs.id", ondelete="SET NULL")
    lane: str = Field(default="backend", max_length=16)
    seq: int
    model: str | None = Field(default=None, max_length=128)
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    thinking_tokens: int | None = None
    started_at: datetime = Field(sa_type=TZDateTime)
    ended_at: datetime = Field(sa_type=TZDateTime)
    duration_ms: int = 0
    latency_source: str = Field(default="measured", max_length=16)
    cost_usd: float | None = None
    cost_source: str | None = Field(default=None, max_length=16)
    tools: list[dict[str, Any]] = Field(default_factory=list, sa_type=Json)
