import uuid
from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime
from typing import Any, TypeVar

from sqlmodel import Session

from src.libs.database import db_session_manager
from src.modules.generations.infrastructure.persistence import ExecutionRecordRepository, GenerationRepository
from src.modules.shared.domain.entities import (
    BackendSpecEntity,
    CliInvocationEntity,
    GenerationEntity,
    NodeRunEntity,
    ValidationRunEntity,
)
from src.modules.specs.infrastructure.persistence import BackendSpecRepository

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

    def spec(self, spec_id: uuid.UUID) -> BackendSpecEntity | None:
        return self._with(lambda s: BackendSpecRepository(s).find_by_id(spec_id))

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
