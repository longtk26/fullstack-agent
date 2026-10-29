from datetime import datetime

from sqlmodel import Field, SQLModel

from ._columns import TZDateTime, utcnow


class ComponentCacheModel(SQLModel, table=True):
    __tablename__ = "component_cache"

    key: str = Field(primary_key=True, max_length=64)
    name: str = Field(max_length=64, index=True)
    source_generation_id: str | None = Field(default=None, max_length=64)
    engine: str = Field(max_length=32)
    model: str | None = Field(default=None, max_length=64)
    hits: int = Field(default=0)
    saved_seconds: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=utcnow, sa_type=TZDateTime)
    last_used_at: datetime = Field(default_factory=utcnow, sa_type=TZDateTime)
