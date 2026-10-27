from typing import Any, TypedDict

from src.modules.shared.domain.enums import GenerationMode, GenerationStatus, Lane, LaneStatus

NODES = (
    "validate_inputs",
    "build_contract",
    "validate_spec",
    "plan_architecture",
    "generate_database",
    "generate_backend",
    "generate_tests",
    "run_validation",
    "repair_code",
    "package_artifacts",
)
BACKEND_NODES = NODES[2:]

# The nodes each mode's graph is built from (Story 12.2; 14.1 adds the parallel frontend lane).
MODE_NODES: dict[GenerationMode, tuple[str, ...]] = {
    GenerationMode.BACKEND: BACKEND_NODES,
    GenerationMode.DYNAMIC: ("validate_inputs", "build_contract", *BACKEND_NODES[1:]),
    GenerationMode.STATIC: ("validate_inputs", "package_artifacts"),
}

NODE_STATUS = {
    "run_validation": GenerationStatus.VALIDATING,
    "repair_code": GenerationStatus.REPAIRING,
}

# Which lane a node belongs to; job-level nodes (inputs, contract, packaging) have none.
NODE_LANE: dict[str, Lane] = {node: Lane.BACKEND for node in BACKEND_NODES if node not in ("package_artifacts",)}


def status_for(node: str) -> GenerationStatus:
    return NODE_STATUS.get(node, GenerationStatus.RUNNING)


def lane_status_for(node: str) -> LaneStatus:
    return LaneStatus(status_for(node).value)


class Outcome:
    COMPLETED = "completed"
    SPEC_INVALID = "spec_invalid"
    REPAIR_LIMIT = "repair_limit"


class GenerationState(TypedDict, total=False):
    """Checkpointed graph state: identifiers and references only — files live in the workspace."""

    generation_id: str
    mode: str
    spec_id: str | None
    frontend_spec_id: str | None
    engine: str
    options: dict[str, Any]
    workspace: str
    spec_valid: bool
    spec_ref: str | None
    frontend_ref: str | None
    contract_ref: str | None
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
