import uuid
from datetime import datetime

from pydantic import BaseModel

# Stored file extension per type (Story 15.4).
UPLOAD_EXTENSIONS = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/svg+xml": "svg"}


class UploadEntity(BaseModel):
    id: str
    owner_id: uuid.UUID
    filename: str
    mime: str
    bytes: int
    width: int | None = None
    height: int | None = None
    sha256: str  # of the uploaded content (the same file uploaded twice is one upload)
    created_at: datetime | None = None

    @property
    def extension(self) -> str:
        return UPLOAD_EXTENSIONS[self.mime]

    @property
    def relative_path(self) -> str:
        """Under the uploads directory (`UPLOAD_ROOT`, by default `<ARTIFACT_ROOT>/uploads`)."""
        return f"{self.owner_id}/{self.id}.{self.extension}"
