import uuid
from datetime import datetime

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Text, UniqueConstraint
from sqlmodel import Field, SQLModel

from src.modules.shared.domain.enums import PreviewStatus

from ._columns import TZDateTime


class PreviewModel(SQLModel, table=True):
    __tablename__ = "previews"
    __table_args__ = (UniqueConstraint("generation_id", "kind", name="uq_previews_generation_id_kind"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    generation_id: str = Field(foreign_key="generations.id", ondelete="CASCADE", index=True, max_length=32)
    # backend | frontend (Story 13.5): a dynamic generation has both
    kind: str = Field(default="backend", max_length=16, sa_column_kwargs={"server_default": "backend"})
    status: PreviewStatus = Field(default=PreviewStatus.STARTING, sa_type=SAEnum(PreviewStatus, name="preview_status"))
    container_id: str | None = Field(default=None, max_length=128)
    db_container_id: str | None = Field(default=None, max_length=128)
    host_port: int | None = None
    url: str | None = None
    started_at: datetime | None = Field(default=None, sa_type=TZDateTime)
    last_accessed_at: datetime | None = Field(default=None, sa_type=TZDateTime)
    expires_at: datetime | None = Field(default=None, sa_type=TZDateTime)
    error: str | None = Field(default=None, sa_type=Text)
    mock_api: bool | None = None  # frontend previews: MOCK_TEST_API (Story 14.2 switches it off)
