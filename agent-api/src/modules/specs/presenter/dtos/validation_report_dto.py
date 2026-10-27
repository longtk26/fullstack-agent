from typing import Any

from src.libs.dtos import CamelModel
from src.modules.shared.domain.backend_spec import SpecIssue, ValidationReport


class SpecIssueDto(CamelModel):
    code: str
    path: str
    message: str
    hint: str | None = None
    severity: str
    backend_path: str | None = None

    @classmethod
    def from_domain(cls, issue: SpecIssue) -> "SpecIssueDto":
        return cls(**issue.model_dump(mode="json"))


class ValidationReportDto(CamelModel):
    valid: bool
    spec_version: str | None
    errors: list[SpecIssueDto]
    warnings: list[SpecIssueDto]

    @classmethod
    def from_domain(cls, report: ValidationReport) -> "ValidationReportDto":
        return cls(
            valid=report.valid,
            spec_version=report.spec_version,
            errors=[SpecIssueDto.from_domain(issue) for issue in report.errors],
            warnings=[SpecIssueDto.from_domain(issue) for issue in report.warnings],
        )


class CheckSpecPairRequestDto(CamelModel):
    frontend_spec: dict[str, Any]
    backend_spec: dict[str, Any]


class SpecPairReportDto(ValidationReportDto):
    """Consistency issues only; `checked` is false when a spec is invalid or the FrontendSpec is static."""

    checked: bool
