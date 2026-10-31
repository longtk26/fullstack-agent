import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from ._columns import TZDateTime, utcnow


class ImageCallModel(SQLModel, table=True):
    """One AI photo generation request (Story 19.2)."""

    __tablename__ = "image_calls"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    generation_id: str | None = Field(
        default=None, foreign_key="generations.id", ondelete="CASCADE", max_length=32, index=True
    )
    draft_id: uuid.UUID | None = Field(default=None, foreign_key="spec_drafts.id", ondelete="CASCADE", index=True)
    node_run_id: uuid.UUID | None = Field(default=None, foreign_key="node_runs.id", ondelete="SET NULL")
    asset_id: str = Field(max_length=64)
    model: str = Field(max_length=128)
    status: str = Field(max_length=16)  # "ok" | "cached" | "blocked" | "failed"
    duration_ms: int = Field(default=0)
    cost_usd: float | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=utcnow, sa_type=TZDateTime, index=True)
