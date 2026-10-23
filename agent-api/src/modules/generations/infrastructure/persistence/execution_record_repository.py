import uuid
from typing import Annotated, Any

from fastapi import Depends
from sqlmodel import col, select, update

from src.libs.database.session import SessionDep
from src.modules.generations.ports.output import IExecutionRecordRepository
from src.modules.shared.domain.entities import CliInvocationEntity, NodeRunEntity, ValidationRunEntity
from src.modules.shared.infrastructure.models import CliInvocationModel, NodeRunModel, ValidationRunModel
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

    def list_validation_runs(self, generation_id: str) -> list[ValidationRunEntity]:
        query = (
            select(ValidationRunModel)
            .where(ValidationRunModel.generation_id == generation_id)
            .order_by(col(ValidationRunModel.created_at))
        )
        return [ValidationRunEntity.model_validate(m.model_dump()) for m in self.session.exec(query)]


IExecutionRecordRepoDep = Annotated[IExecutionRecordRepository, Depends(ExecutionRecordRepository)]
