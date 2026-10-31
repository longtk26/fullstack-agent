import uuid
from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from ._columns import TZDateTime, utcnow


class UploadModel(SQLModel, table=True):
    """A user's image for generated sites (Story 15.4): `ARTIFACT_ROOT/uploads/<owner>/<id>.<ext>`. One row per file
    content and owner (the same file uploaded twice is the same upload)."""

    __tablename__ = "uploads"
    __table_args__ = (UniqueConstraint("owner_id", "sha256", name="uq_uploads_owner_sha256"),)

    id: str = Field(primary_key=True, max_length=40)
    owner_id: uuid.UUID = Field(foreign_key="users.id", ondelete="CASCADE", index=True)
    filename: str = Field(max_length=255)
    mime: str = Field(max_length=64)
    bytes: int
    width: int | None = None
    height: int | None = None
    sha256: str = Field(max_length=64)
    origin: str = Field(default="user", max_length=16)
    prompt: str | None = None
    created_at: datetime = Field(default_factory=utcnow, sa_type=TZDateTime, index=True)
