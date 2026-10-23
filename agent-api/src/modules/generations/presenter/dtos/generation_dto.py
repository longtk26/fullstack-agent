import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import ConfigDict, Field, model_validator

from src.libs.dtos import CamelModel
from src.modules.shared.domain.enums import GenerationStatus


class GenerationOptionsDto(CamelModel):
    model_config = ConfigDict(extra="forbid")

    max_repair_attempts: int = Field(default=3, ge=0, le=10)
    run_tests: bool = True
    generate_dockerfile: bool = True
    deploy_preview: bool = True
    engine: Literal["claude_code", "antigravity", "fake"] | None = None
    timeout_seconds: int | None = Field(default=None, ge=60, le=7200)


class CreateGenerationRequestDto(CamelModel):
    backend_spec: dict[str, Any] | None = None
    spec_id: uuid.UUID | None = None
    options: GenerationOptionsDto = GenerationOptionsDto()

    @model_validator(mode="after")
    def _exactly_one_spec_source(self):
        if (self.backend_spec is None) == (self.spec_id is None):
            raise ValueError("Provide exactly one of 'backendSpec' or 'specId'")
        return self


class CreateGenerationResponseDto(CamelModel):
    generation_id: str
    status: GenerationStatus
    created_at: datetime | None


class StepDto(CamelModel):
    node: str
    attempt: int
    status: str
    started_at: datetime | None
    finished_at: datetime | None


class GenerationDetailDto(CamelModel):
    generation_id: str
    spec_id: str
    project_name: str | None
    status: GenerationStatus
    current_step: str | None
    engine: str
    options: dict[str, Any]
    repair_attempts: int
    resume_count: int
    cancel_requested: bool
    validation: dict[str, str]
    steps: list[StepDto]
    artifacts: dict[str, str]
    preview: dict[str, Any] | None
    trace: dict[str, Any]
    error: str | None
    created_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None


class GenerationSummaryDto(CamelModel):
    generation_id: str
    project_name: str | None
    status: GenerationStatus
    current_step: str | None
    engine: str
    repair_attempts: int
    created_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None


class GenerationPageDto(CamelModel):
    items: list[GenerationSummaryDto]
    next_cursor: str | None


class CancelGenerationResponseDto(CamelModel):
    generation_id: str
    status: GenerationStatus
    cancel_requested: bool
