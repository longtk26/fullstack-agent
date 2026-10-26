from datetime import datetime
from typing import Any

from src.libs.dtos import CamelModel
from src.modules.shared.domain.entities import PreviewEntity
from src.modules.shared.domain.enums import PreviewStatus


class PreviewDto(CamelModel):
    generation_id: str
    status: PreviewStatus
    url: str | None
    openapi_url: str | None
    docs_url: str | None
    host_port: int | None
    started_at: datetime | None
    last_accessed_at: datetime | None
    expires_at: datetime | None
    error: str | None

    @classmethod
    def from_entity(cls, preview: PreviewEntity) -> "PreviewDto":
        return cls(
            generation_id=preview.generation_id,
            status=preview.status,
            url=preview.url,
            openapi_url=f"{preview.url}/openapi.json" if preview.url else None,
            docs_url=f"{preview.url}/docs" if preview.url else None,
            host_port=preview.host_port,
            started_at=preview.started_at,
            last_accessed_at=preview.last_accessed_at,
            expires_at=preview.expires_at,
            error=preview.error,
        )


class PreviewListDto(CamelModel):
    items: list[PreviewDto]


class PreviewLogsDto(CamelModel):
    lines: list[str]


class PreviewRequestDto(CamelModel):
    ts: str
    method: str
    path: str
    route: str | None
    operation_id: str | None
    status: int
    duration_ms: float | None


class PreviewRequestsDto(CamelModel):
    items: list[PreviewRequestDto]
    cursor: str | None

    @classmethod
    def from_reply(cls, reply: dict[str, Any]) -> "PreviewRequestsDto":
        return cls.model_validate(reply)
