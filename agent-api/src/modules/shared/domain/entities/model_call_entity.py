import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ModelCallEntity(BaseModel):
    id: uuid.UUID | None = None
    generation_id: str
    cli_invocation_id: uuid.UUID
    node_run_id: uuid.UUID | None = None
    lane: str = "backend"
    seq: int
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    thinking_tokens: int | None = None
    started_at: datetime
    ended_at: datetime
    duration_ms: int = 0
    latency_source: str = "measured"
    cost_usd: float | None = None
    cost_source: str | None = None
    tools: list[dict[str, Any]] = []
