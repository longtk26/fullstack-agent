from datetime import datetime

from src.libs.dtos import CamelModel
from src.modules.shared.domain.entities import UploadEntity


class UploadDto(CamelModel):
    upload_id: str
    source: str  # what a FrontendSpec asset uses: `upload:<id>`
    filename: str
    mime: str
    bytes: int
    width: int | None
    height: int | None
    sha256: str
    origin: str = "user"
    prompt: str | None = None
    created_at: datetime | None

    @classmethod
    def from_entity(cls, upload: UploadEntity) -> "UploadDto":
        return cls(
            upload_id=upload.id,
            source=f"upload:{upload.id}",
            filename=upload.filename,
            mime=upload.mime,
            bytes=upload.bytes,
            width=upload.width,
            height=upload.height,
            sha256=upload.sha256,
            origin=upload.origin,
            prompt=upload.prompt,
            created_at=upload.created_at,
        )


class UploadListDto(CamelModel):
    uploads: list[UploadDto]
    used_bytes: int
    quota_bytes: int


__all__ = ["UploadDto", "UploadListDto"]
