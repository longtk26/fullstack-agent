import uuid
from typing import Annotated, Any

from fastapi import Depends
from sqlmodel import col, delete, select, update

from src.libs.database.session import SessionDep
from src.modules.generations.ports.output import IExecutionRecordRepository
from src.modules.shared.domain.entities import (
    CliInvocationEntity,
    ImageCallEntity,
    ModelCallEntity,
    NodeRunEntity,
    SandboxExecEntity,
    ValidationRunEntity,
)
from src.modules.shared.infrastructure.models import (
    CliInvocationModel,
    ImageCallModel,
    ModelCallModel,
    NodeRunModel,
    SandboxExecModel,
    ValidationRunModel,
)
from src.modules.shared.infrastructure.models._columns import utcnow


class ExecutionRecordRepository(IExecutionRecordRepository):
    def __init__(self, session: SessionDep):
        self.session = session

    def start_node_run(self, run: NodeRunEntity) -> NodeRunEntity:
        model = NodeRunModel(**run.model_dump(exclude_none=True))
        self.session.add(model)
        self.session.flush()
        return NodeRunEntity.model_validate(model.model_dump())

    def finish_node_run(self, run_id: uuid.UUID, status: str, summary: dict[str, Any]) -> None:
        model = self.session.get(NodeRunModel, run_id)
        model.status, model.summary, model.finished_at = status, summary, utcnow()
        self.session.flush()

    def abandon_running(self, generation_id: str) -> int:
        abandoned = 0
        for model in (NodeRunModel, CliInvocationModel):
            result = self.session.exec(
                update(model)
                .where(model.generation_id == generation_id, model.status == "running")
                .values(status="abandoned")
            )
            abandoned += result.rowcount
        self.session.flush()
        return abandoned

    def add_cli_invocation(self, invocation: CliInvocationEntity) -> CliInvocationEntity:
        model = CliInvocationModel(**invocation.model_dump(exclude_none=True))
        self.session.add(model)
        self.session.flush()
        return CliInvocationEntity.model_validate(model.model_dump())

    def update_cli_invocation(self, invocation_id: uuid.UUID, **fields: Any) -> None:
        model = self.session.get(CliInvocationModel, invocation_id)
        for key, value in fields.items():
            setattr(model, key, value)
        self.session.flush()

    def add_validation_run(self, run: ValidationRunEntity) -> ValidationRunEntity:
        model = ValidationRunModel(**run.model_dump(exclude_none=True))
        self.session.add(model)
        self.session.flush()
        return ValidationRunEntity.model_validate(model.model_dump())

    def list_node_runs(self, generation_id: str) -> list[NodeRunEntity]:
        query = (
            select(NodeRunModel)
            .where(NodeRunModel.generation_id == generation_id)
            .order_by(col(NodeRunModel.started_at))
        )
        return [NodeRunEntity.model_validate(m.model_dump()) for m in self.session.exec(query)]

    def list_cli_invocations(self, generation_id: str) -> list[CliInvocationEntity]:
        query = (
            select(CliInvocationModel)
            .where(CliInvocationModel.generation_id == generation_id)
            .order_by(col(CliInvocationModel.created_at))
        )
        return [CliInvocationEntity.model_validate(m.model_dump()) for m in self.session.exec(query)]

    def list_validation_runs(self, generation_id: str) -> list[ValidationRunEntity]:
        query = (
            select(ValidationRunModel)
            .where(ValidationRunModel.generation_id == generation_id)
            .order_by(col(ValidationRunModel.created_at))
        )
        return [ValidationRunEntity.model_validate(m.model_dump()) for m in self.session.exec(query)]

    def add_model_calls(self, calls: list[ModelCallEntity]) -> None:
        self.session.add_all(ModelCallModel(**call.model_dump(exclude_none=True)) for call in calls)
        self.session.flush()

    def list_model_calls(self, generation_id: str) -> list[ModelCallEntity]:
        query = (
            select(ModelCallModel)
            .where(ModelCallModel.generation_id == generation_id)
            .order_by(col(ModelCallModel.started_at), col(ModelCallModel.seq))
        )
        return [ModelCallEntity.model_validate(m.model_dump()) for m in self.session.exec(query)]

    def add_image_calls(self, calls: list[ImageCallEntity]) -> None:
        self.session.add_all(ImageCallModel(**call.model_dump(exclude_none=True)) for call in calls)
        self.session.flush()

    def list_image_calls(self, generation_id: str) -> list[ImageCallEntity]:
        query = (
            select(ImageCallModel)
            .where(ImageCallModel.generation_id == generation_id)
            .order_by(col(ImageCallModel.created_at))
        )
        return [ImageCallEntity.model_validate(m.model_dump()) for m in self.session.exec(query)]

    def list_draft_image_calls(self, draft_id: Any) -> list[ImageCallEntity]:
        query = (
            select(ImageCallModel).where(ImageCallModel.draft_id == draft_id).order_by(col(ImageCallModel.created_at))
        )
        return [ImageCallEntity.model_validate(m.model_dump()) for m in self.session.exec(query)]

    def add_sandbox_exec(self, run: SandboxExecEntity) -> None:
        self.session.add(SandboxExecModel(**run.model_dump(exclude_none=True)))
        self.session.flush()

    def list_sandbox_execs(self, generation_id: str) -> list[SandboxExecEntity]:
        query = (
            select(SandboxExecModel)
            .where(SandboxExecModel.generation_id == generation_id)
            .order_by(col(SandboxExecModel.started_at))
        )
        return [SandboxExecEntity.model_validate(m.model_dump()) for m in self.session.exec(query)]

    def records_for(self, generation_ids: list[str]) -> dict[str, dict[str, list]]:
        result: dict[str, dict[str, list]] = {gid: {kind: [] for kind, _, _, _ in _BULK} for gid in generation_ids}
        if not generation_ids:
            return result
        for kind, model, entity, order in _BULK:
            query = select(model).where(col(model.generation_id).in_(generation_ids)).order_by(col(order))
            for row in self.session.exec(query):
                result[row.generation_id][kind].append(entity.model_validate(row.model_dump()))
        return result

    def prune_details(self, generation_ids: list[str]) -> int:
        if not generation_ids:
            return 0
        removed = 0
        for model in (ModelCallModel, SandboxExecModel, ImageCallModel):
            removed += self.session.exec(delete(model).where(col(model.generation_id).in_(generation_ids))).rowcount
        self.session.flush()
        return removed


_BULK = (
    ("node_runs", NodeRunModel, NodeRunEntity, NodeRunModel.started_at),
    ("invocations", CliInvocationModel, CliInvocationEntity, CliInvocationModel.created_at),
    ("model_calls", ModelCallModel, ModelCallEntity, ModelCallModel.started_at),
    ("image_calls", ImageCallModel, ImageCallEntity, ImageCallModel.created_at),
    ("validation_runs", ValidationRunModel, ValidationRunEntity, ValidationRunModel.created_at),
    ("sandbox_execs", SandboxExecModel, SandboxExecEntity, SandboxExecModel.started_at),
)

IExecutionRecordRepoDep = Annotated[IExecutionRecordRepository, Depends(ExecutionRecordRepository)]
