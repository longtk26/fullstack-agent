import uuid
from datetime import datetime

from pydantic import BaseModel


class CliInvocationEntity(BaseModel):
    id: uuid.UUID | None = None
    generation_id: str
    node_run_id: uuid.UUID | None = None
    engine: str
    purpose: str
    argv_redacted: list[str] = []
    exit_code: int | None = None
    status: str
    duration_ms: int | None = None
    turns: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    cost_source: str | None = None
    model: str | None = None
    cache_read_tokens: int | None = None
    cache_write_tokens: int | None = None
    thinking_tokens: int | None = None
    prompt_ref: str | None = None
    error_reason: str | None = None
    changed_files: list[str] = []
    finished_at: datetime | None = None
    stdout_ref: str | None = None
    stderr_ref: str | None = None
    created_at: datetime | None = None
