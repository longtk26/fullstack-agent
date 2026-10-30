from datetime import datetime
from typing import Any, Literal

from src.libs.dtos import CamelModel
from src.modules.shared.domain.backend_spec import ValidationReport
from src.modules.shared.domain.entities import SpecDraftEntity
from src.modules.shared.domain.enums import GenerationMode, SpecDraftStatus, SpecSource

from .validation_report_dto import ValidationReportDto


class CreateSpecDraftRequestDto(CamelModel):
    """`source=requirement`: `requirementText` (plain text or Markdown, typed or read from a .md / .txt file whose
    name goes in `requirementFileName`). `source=frontend` (2.5 "Refine with AI", mode backend): `baseSpec` +
    `siteJson`."""

    source: SpecSource = SpecSource.REQUIREMENT
    mode: GenerationMode = GenerationMode.BACKEND
    requirement_text: str | None = None
    requirement_format: Literal["text", "markdown"] | None = None
    requirement_file_name: str | None = None
    base_spec: dict[str, Any] | None = None
    site_json: dict[str, Any] | None = None
    engine: str | None = None


class CreateSpecDraftResponseDto(CamelModel):
    draft_id: str
    status: SpecDraftStatus


class DraftNoteDto(CamelModel):
    path: str
    message: str
    suggestion: str | None = None
    spec: Literal["backend", "frontend"] | None = None


class DraftValidationDto(CamelModel):
    backend: ValidationReportDto | None = None
    frontend: ValidationReportDto | None = None
    pair: ValidationReportDto | None = None


class RequirementInfoDto(CamelModel):
    text: str | None
    format: str | None
    file_name: str | None


class GetSpecDraftResponseDto(CamelModel):
    draft_id: str
    status: SpecDraftStatus
    progress: str | None
    source: SpecSource
    mode: GenerationMode
    engine: str
    attempts: int
    requirement: RequirementInfoDto
    backend_spec: dict[str, Any] | None
    frontend_spec: dict[str, Any] | None
    assumptions: list[DraftNoteDto]
    unresolved: list[DraftNoteDto]
    design: dict[str, Any] | None
    validation: DraftValidationDto
    usage: dict[str, Any]
    error: str | None
    created_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None

    @classmethod
    def from_entity(cls, draft: SpecDraftEntity) -> "GetSpecDraftResponseDto":
        reports = {
            key: ValidationReportDto.from_domain(ValidationReport.model_validate(value))
            for key, value in draft.validation.items()
            if key in ("backend", "frontend", "pair") and value
        }
        return cls(
            draft_id=str(draft.id),
            status=draft.status,
            progress=draft.progress,
            source=draft.source,
            mode=draft.mode,
            engine=draft.engine,
            attempts=draft.attempts,
            requirement=RequirementInfoDto(
                text=draft.requirement_text, format=draft.requirement_format, file_name=draft.requirement_file_name
            ),
            backend_spec=draft.backend_spec,
            frontend_spec=draft.frontend_spec,
            assumptions=[DraftNoteDto.model_validate(note) for note in draft.assumptions],
            unresolved=[DraftNoteDto.model_validate(note) for note in draft.unresolved],
            design=draft.design,
            validation=DraftValidationDto(**reports),
            usage=draft.usage,
            error=draft.error,
            created_at=draft.created_at,
            started_at=draft.started_at,
            finished_at=draft.finished_at,
        )
