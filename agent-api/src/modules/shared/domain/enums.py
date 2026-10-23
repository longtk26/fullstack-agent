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
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

    @property
    def is_terminal(self) -> bool:
        return self in {GenerationStatus.COMPLETED, GenerationStatus.FAILED, GenerationStatus.CANCELLED}


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
