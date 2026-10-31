import uuid
from abc import ABC, abstractmethod
from typing import Any

from src.modules.shared.domain.entities import (
    CliInvocationEntity,
    ImageCallEntity,
    ModelCallEntity,
    NodeRunEntity,
    SandboxExecEntity,
    ValidationRunEntity,
)


class IExecutionRecordRepository(ABC):
    """node_runs, cli_invocations, model_calls, validation_runs and sandbox_execs: what the worker did, step by
    step. The local trace (Story 8.3) and the usage rollups (8.4) are built from these."""

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

    @abstractmethod
    def list_cli_invocations(self, generation_id: str) -> list[CliInvocationEntity]:
        pass

    @abstractmethod
    def add_model_calls(self, calls: list[ModelCallEntity]) -> None:
        pass

    @abstractmethod
    def list_model_calls(self, generation_id: str) -> list[ModelCallEntity]:
        pass

    @abstractmethod
    def add_image_calls(self, calls: list[ImageCallEntity]) -> None:
        pass

    @abstractmethod
    def list_image_calls(self, generation_id: str) -> list[ImageCallEntity]:
        pass

    @abstractmethod
    def list_draft_image_calls(self, draft_id: Any) -> list[ImageCallEntity]:
        pass

    @abstractmethod
    def add_sandbox_exec(self, run: SandboxExecEntity) -> None:
        pass

    @abstractmethod
    def list_sandbox_execs(self, generation_id: str) -> list[SandboxExecEntity]:
        pass

    @abstractmethod
    def prune_details(self, generation_ids: list[str]) -> int:
        """Deletes model calls and sandbox records of these generations (trace retention)."""

    @abstractmethod
    def records_for(self, generation_ids: list[str]) -> dict[str, dict[str, list]]:
        """Every record of these generations at once, keyed by generation id and then by kind (`node_runs`,
        `invocations`, `model_calls`, `validation_runs`, `sandbox_execs`)."""
