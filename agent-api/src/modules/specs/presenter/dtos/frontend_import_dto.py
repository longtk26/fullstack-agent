from typing import Any

from src.libs.dtos import CamelModel
from src.modules.shared.domain.frontend_site import FrontendImportResult

from .validation_report_dto import ValidationReportDto


class ImportNoteDto(CamelModel):
    path: str
    message: str
    suggestion: str | None = None


class FrontendImportResponseDto(CamelModel):
    backend_spec: dict[str, Any]
    seed: list[dict[str, Any]]
    assumptions: list[ImportNoteDto]
    unresolved: list[ImportNoteDto]
    bindings: list[dict[str, Any]]
    validation: ValidationReportDto

    @classmethod
    def from_domain(cls, result: FrontendImportResult) -> "FrontendImportResponseDto":
        return cls(
            backend_spec=result.backend_spec,
            seed=result.seed,
            assumptions=[ImportNoteDto(**note.model_dump()) for note in result.assumptions],
            unresolved=[ImportNoteDto(**note.model_dump()) for note in result.unresolved],
            bindings=result.bindings,
            validation=ValidationReportDto.from_domain(result.validation),
        )
