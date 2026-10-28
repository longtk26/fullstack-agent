"""Generation modes and lanes (Story 12.2): which lanes a mode runs and how lane outcomes make the overall status.

    backend  → backend
    static   → frontend
    dynamic  → backend, frontend, integration (the switch from mocks to the live API, Epic 14)

Overall status once the workflow has ended: every lane COMPLETED → COMPLETED. In `dynamic` mode a FAILED backend
with a COMPLETED frontend (still working on mocks, 14.2) → COMPLETED_WITH_WARNINGS. Any other FAILED lane →
FAILED. Lanes that were SKIPPED (for example not available yet) next to completed ones → COMPLETED_WITH_WARNINGS.
"""

from src.modules.shared.domain.enums import GenerationMode, GenerationStatus, Lane, LaneStatus

LANES: dict[GenerationMode, tuple[Lane, ...]] = {
    GenerationMode.BACKEND: (Lane.BACKEND,),
    GenerationMode.STATIC: (Lane.FRONTEND,),
    GenerationMode.DYNAMIC: (Lane.BACKEND, Lane.FRONTEND, Lane.INTEGRATION),
}

# Lanes this build cannot run yet, with the reason the job reports. Epic 14 brings the integration lane (the
# switch from mocks to the live backend), so every lane is now runnable.
UNAVAILABLE_LANES: dict[Lane, str] = {}


def initial_lanes(mode: GenerationMode) -> dict[str, str]:
    return {lane.value: LaneStatus.PENDING.value for lane in LANES[mode]}


def overall_status(mode: GenerationMode, lanes: dict[str, str]) -> GenerationStatus:
    statuses = {lane: LaneStatus(lanes.get(lane.value, LaneStatus.PENDING)) for lane in LANES[mode]}
    if all(status == LaneStatus.COMPLETED for status in statuses.values()):
        return GenerationStatus.COMPLETED
    if (
        mode == GenerationMode.DYNAMIC
        and statuses[Lane.FRONTEND] == LaneStatus.COMPLETED
        and statuses[Lane.BACKEND] in (LaneStatus.COMPLETED, LaneStatus.FAILED, LaneStatus.SKIPPED)
        and statuses[Lane.INTEGRATION] in (LaneStatus.COMPLETED, LaneStatus.FAILED, LaneStatus.SKIPPED)
    ):
        return GenerationStatus.COMPLETED_WITH_WARNINGS
    if any(status not in (LaneStatus.COMPLETED, LaneStatus.SKIPPED) for status in statuses.values()):
        return GenerationStatus.FAILED
    return GenerationStatus.COMPLETED_WITH_WARNINGS


def close_lanes(lanes: dict[str, str], failed: bool) -> dict[str, str]:
    """When a job ends early: active lanes FAILED (or SKIPPED on cancel), lanes that never started SKIPPED."""
    closed = {}
    for lane, status in lanes.items():
        current = LaneStatus(status)
        if current.is_terminal:
            closed[lane] = status
        elif failed and current != LaneStatus.PENDING:
            closed[lane] = LaneStatus.FAILED.value
        else:
            closed[lane] = LaneStatus.SKIPPED.value
    return closed


def backend_ready(status: GenerationStatus, lanes: dict[str, str]) -> bool:
    """A generation whose backend was built, packaged and can be previewed."""
    if not lanes:  # rows written without lanes are backend jobs
        return status in (GenerationStatus.COMPLETED, GenerationStatus.COMPLETED_WITH_WARNINGS)
    if status in (GenerationStatus.FAILED, GenerationStatus.CANCELLED):
        return False
    return lanes.get(Lane.BACKEND.value) == LaneStatus.COMPLETED.value
