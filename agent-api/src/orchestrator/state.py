from typing import Any, TypedDict

from src.modules.shared.domain.enums import GenerationStatus

NODES = (
    "validate_spec",
    "plan_architecture",
    "generate_database",
    "generate_backend",
    "generate_tests",
    "run_validation",
    "repair_code",
    "package_artifacts",
)

NODE_STATUS = {
    "run_validation": GenerationStatus.VALIDATING,
    "repair_code": GenerationStatus.REPAIRING,
}


def status_for(node: str) -> GenerationStatus:
    return NODE_STATUS.get(node, GenerationStatus.RUNNING)


class Outcome:
    COMPLETED = "completed"
    SPEC_INVALID = "spec_invalid"
    REPAIR_LIMIT = "repair_limit"


class GenerationState(TypedDict, total=False):
    """Checkpointed graph state: identifiers and references only — files live in the workspace."""

    generation_id: str
    spec_id: str
    engine: str
    options: dict[str, Any]
    workspace: str
    spec_valid: bool
    spec_ref: str | None
    plan_ref: str | None
    repair_attempts: int
    max_repair_attempts: int
    validation: dict[str, str]
    failed_checks: list[str]
    failure_digest_ref: str | None
    implicated_files: list[str]
    error_summary: str | None
    artifact_ids: dict[str, str]
    last_commit: str | None
    outcome: str | None
