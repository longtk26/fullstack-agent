import uuid
from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime
from typing import Any, TypeVar

from sqlmodel import Session

from src.libs.database import db_session_manager
from src.modules.generations.infrastructure.persistence import (
    ArtifactRepository,
    ExecutionRecordRepository,
    GenerationRepository,
)
from src.modules.previews.infrastructure.persistence import PreviewRepository
from src.modules.shared.domain.entities import (
    ArtifactEntity,
    BackendSpecEntity,
    CliInvocationEntity,
    FrontendSpecEntity,
    GenerationEntity,
    ModelCallEntity,
    NodeRunEntity,
    PreviewEntity,
    SandboxExecEntity,
    ValidationRunEntity,
)
from src.modules.shared.domain.enums import PreviewStatus
from src.modules.specs.infrastructure.persistence import BackendSpecRepository, FrontendSpecRepository

T = TypeVar("T")


@contextmanager
def _session():
    with Session(db_session_manager.engine) as session:
        yield session
        session.commit()


class JobStore:
    """The worker's DB access: one short transaction per call, so no session outlives a graph step."""

    def _with(self, fn: Callable[[Session], T]) -> T:
        with _session() as session:
            return fn(session)

    def generation(self, generation_id: str) -> GenerationEntity | None:
        return self._with(lambda s: GenerationRepository(s).find_by_id(generation_id))

    def update_generation(self, generation_id: str, **fields: Any) -> GenerationEntity:
        return self._with(lambda s: GenerationRepository(s).update(generation_id, **fields))

    def stale_active(self, heartbeat_before: datetime) -> list[GenerationEntity]:
        return self._with(lambda s: GenerationRepository(s).find_stale_active(heartbeat_before))

    def pending_before(self, created_before: datetime) -> list[GenerationEntity]:
        return self._with(lambda s: GenerationRepository(s).find_pending_created_before(created_before))

    def finished_before(self, finished_before: datetime) -> list[str]:
        return self._with(lambda s: GenerationRepository(s).find_finished_before(finished_before))

    def spec(self, spec_id: uuid.UUID | None) -> BackendSpecEntity | None:
        if spec_id is None:
            return None
        return self._with(lambda s: BackendSpecRepository(s).find_by_id(spec_id))

    def frontend_spec(self, spec_id: uuid.UUID | None) -> FrontendSpecEntity | None:
        if spec_id is None:
            return None
        return self._with(lambda s: FrontendSpecRepository(s).find_by_id(spec_id))

    def start_node(self, generation_id: str, node: str, attempt: int) -> uuid.UUID:
        run = NodeRunEntity(generation_id=generation_id, node=node, attempt=attempt, status="running")
        return self._with(lambda s: ExecutionRecordRepository(s).start_node_run(run)).id

    def finish_node(self, run_id: uuid.UUID, status: str, summary: dict[str, Any]) -> None:
        self._with(lambda s: ExecutionRecordRepository(s).finish_node_run(run_id, status, summary))

    def abandon_running(self, generation_id: str) -> int:
        return self._with(lambda s: ExecutionRecordRepository(s).abandon_running(generation_id))

    def add_cli_invocation(self, invocation: CliInvocationEntity) -> uuid.UUID:
        return self._with(lambda s: ExecutionRecordRepository(s).add_cli_invocation(invocation)).id

    def update_cli_invocation(self, invocation_id: uuid.UUID, **fields: Any) -> None:
        self._with(lambda s: ExecutionRecordRepository(s).update_cli_invocation(invocation_id, **fields))

    def add_validation_run(self, run: ValidationRunEntity) -> None:
        self._with(lambda s: ExecutionRecordRepository(s).add_validation_run(run))

    def node_runs(self, generation_id: str) -> list[NodeRunEntity]:
        return self._with(lambda s: ExecutionRecordRepository(s).list_node_runs(generation_id))

    def validation_runs(self, generation_id: str) -> list[ValidationRunEntity]:
        return self._with(lambda s: ExecutionRecordRepository(s).list_validation_runs(generation_id))

    def cli_invocations(self, generation_id: str) -> list[CliInvocationEntity]:
        return self._with(lambda s: ExecutionRecordRepository(s).list_cli_invocations(generation_id))

    def add_model_calls(self, calls: list[ModelCallEntity]) -> None:
        if calls:
            self._with(lambda s: ExecutionRecordRepository(s).add_model_calls(calls))

    def model_calls(self, generation_id: str) -> list[ModelCallEntity]:
        return self._with(lambda s: ExecutionRecordRepository(s).list_model_calls(generation_id))

    def add_sandbox_exec(self, run: SandboxExecEntity) -> None:
        self._with(lambda s: ExecutionRecordRepository(s).add_sandbox_exec(run))

    def sandbox_execs(self, generation_id: str) -> list[SandboxExecEntity]:
        return self._with(lambda s: ExecutionRecordRepository(s).list_sandbox_execs(generation_id))

    def prune_trace_details(self, generation_ids: list[str]) -> int:
        return self._with(lambda s: ExecutionRecordRepository(s).prune_details(generation_ids))

    # -- artifacts (Story 7.1) ----------------------------------------------------------------------------------

    def replace_artifacts(self, generation_id: str, artifacts: list[ArtifactEntity]) -> None:
        self._with(lambda s: ArtifactRepository(s).replace_for_generation(generation_id, artifacts))

    def artifacts(self, generation_id: str) -> list[ArtifactEntity]:
        return self._with(lambda s: ArtifactRepository(s).list_for_generation(generation_id))

    def artifact_by_name(self, generation_id: str, name: str) -> ArtifactEntity | None:
        return self._with(lambda s: ArtifactRepository(s).find_by_name(generation_id, name))

    # -- previews (Stories 7.3, 7.4) ----------------------------------------------------------------------------

    def preview(self, generation_id: str, kind: str = "backend") -> PreviewEntity | None:
        return self._with(lambda s: PreviewRepository(s).find(generation_id, kind))

    def upsert_preview(self, generation_id: str, kind: str = "backend", **fields: Any) -> PreviewEntity:
        return self._with(lambda s: PreviewRepository(s).upsert(generation_id, kind, **fields))

    def delete_preview(self, generation_id: str, kind: str = "backend") -> None:
        self._with(lambda s: PreviewRepository(s).delete(generation_id, kind))

    def previews(self, statuses: tuple[PreviewStatus, ...] | None = None) -> list[PreviewEntity]:
        if statuses is None:
            return self._with(lambda s: PreviewRepository(s).list_all())
        return self._with(lambda s: PreviewRepository(s).list_by_status(statuses))
