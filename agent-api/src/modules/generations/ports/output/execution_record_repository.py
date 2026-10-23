import uuid
from abc import ABC, abstractmethod
from typing import Any

from src.modules.shared.domain.entities import CliInvocationEntity, NodeRunEntity, ValidationRunEntity


class IExecutionRecordRepository(ABC):
    """node_runs, cli_invocations and validation_runs: what the worker did, step by step."""

    @abstractmethod
    def start_node_run(self, run: NodeRunEntity) -> NodeRunEntity:
        pass

    @abstractmethod
    def finish_node_run(self, run_id: uuid.UUID, status: str, summary: dict[str, Any]) -> None:
        pass

    @abstractmethod
    def abandon_running(self, generation_id: str) -> int:
        """Marks node runs / CLI invocations left 'running' by a crashed worker as 'abandoned'."""

    @abstractmethod
    def add_cli_invocation(self, invocation: CliInvocationEntity) -> CliInvocationEntity:
        pass

    @abstractmethod
    def update_cli_invocation(self, invocation_id: uuid.UUID, **fields: Any) -> None:
        pass

    @abstractmethod
    def add_validation_run(self, run: ValidationRunEntity) -> ValidationRunEntity:
        pass

    @abstractmethod
    def list_node_runs(self, generation_id: str) -> list[NodeRunEntity]:
        pass

    @abstractmethod
    def list_validation_runs(self, generation_id: str) -> list[ValidationRunEntity]:
        pass
