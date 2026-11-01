from enum import StrEnum


class UserRole(StrEnum):
    USER = "USER"
    ADMIN = "ADMIN"


class GenerationStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    VALIDATING = "VALIDATING"
    REPAIRING = "REPAIRING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"  # a lane was skipped or failed but the result works (12.2)
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    DRAFTING = "DRAFTING"
    NEEDS_REVIEW = "NEEDS_REVIEW"

    @property
    def is_terminal(self) -> bool:
        return self in TERMINAL_STATUSES


TERMINAL_STATUSES = frozenset(
    {
        GenerationStatus.COMPLETED,
        GenerationStatus.COMPLETED_WITH_WARNINGS,
        GenerationStatus.FAILED,
        GenerationStatus.CANCELLED,
    }
)


class GenerationMode(StrEnum):
    """Story 12.2: what a generation builds."""

    BACKEND = "backend"  # FastAPI backend only
    STATIC = "static"  # frontend only, content baked in
    DYNAMIC = "dynamic"  # frontend + backend from one API contract


class Lane(StrEnum):
    BACKEND = "backend"
    FRONTEND = "frontend"
    INTEGRATION = "integration"


class LaneStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    VALIDATING = "VALIDATING"
    REPAIRING = "REPAIRING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"

    @property
    def is_terminal(self) -> bool:
        return self in {LaneStatus.COMPLETED, LaneStatus.FAILED, LaneStatus.SKIPPED}


class PreviewStatus(StrEnum):
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class SpecSource(StrEnum):
    JSON = "json"
    REQUIREMENT = "requirement"
    FRONTEND = "frontend"


class SpecDraftStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
