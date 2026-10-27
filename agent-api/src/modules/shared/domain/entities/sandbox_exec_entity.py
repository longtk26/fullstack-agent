import uuid
from datetime import datetime

from pydantic import BaseModel


class SandboxExecEntity(BaseModel):
    id: uuid.UUID | None = None
    generation_id: str
    node_run_id: uuid.UUID | None = None
    name: str
    command: str
    status: str
    exit_code: int | None = None
    started_at: datetime
    duration_ms: int = 0
