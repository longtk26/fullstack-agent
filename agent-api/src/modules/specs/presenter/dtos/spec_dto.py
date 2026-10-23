from datetime import datetime
from typing import Any

from src.libs.dtos import CamelModel
from src.modules.shared.domain.entities import BackendSpecEntity
from src.modules.shared.domain.enums import SpecSource

from .validation_report_dto import SpecIssueDto


class CreateSpecResponseDto(CamelModel):
    spec_id: str
    spec_version: str
    warnings: list[SpecIssueDto]


class GetSpecResponseDto(CamelModel):
    id: str
    spec_version: str
    source: SpecSource
    raw: str
    normalized: dict[str, Any] | None
    created_at: datetime | None

    @classmethod
    def from_entity(cls, spec: BackendSpecEntity) -> "GetSpecResponseDto":
        return cls(
            id=str(spec.id),
            spec_version=spec.spec_version,
            source=spec.source,
            raw=spec.raw_json,
            normalized=spec.normalized_json,
            created_at=spec.created_at,
        )
