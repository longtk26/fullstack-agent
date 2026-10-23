from datetime import datetime

from sqlalchemy import BigInteger
from sqlmodel import Field, SQLModel

from ._columns import TZDateTime, utcnow


class ArtifactModel(SQLModel, table=True):
    __tablename__ = "artifacts"

    id: str = Field(primary_key=True, max_length=32)
    generation_id: str = Field(foreign_key="generations.id", ondelete="CASCADE", index=True, max_length=32)
    kind: str = Field(max_length=32)
    name: str = Field(max_length=255)
    path: str
    size: int = Field(sa_type=BigInteger)
    sha256: str = Field(max_length=64)
    content_type: str = Field(max_length=128)
    created_at: datetime = Field(default_factory=utcnow, sa_type=TZDateTime)
