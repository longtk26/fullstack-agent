from datetime import datetime

from pydantic import BaseModel


class ArtifactEntity(BaseModel):
    id: str
    generation_id: str
    kind: str
    name: str
    path: str
    size: int
    sha256: str
    content_type: str
    created_at: datetime | None = None
