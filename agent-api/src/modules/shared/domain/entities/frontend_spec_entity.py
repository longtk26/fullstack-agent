import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from src.modules.shared.domain.enums import SpecSource


class FrontendSpecEntity(BaseModel):
    id: uuid.UUID | None = None
    owner_id: uuid.UUID
    spec_version: str
    mode: str | None = None  # project.mode of a valid spec: static | dynamic
    raw_json: str
    normalized_json: dict[str, Any] | None = None
    source: SpecSource = SpecSource.JSON
    requirement_text: str | None = None
    created_at: datetime | None = None
