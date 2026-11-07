import uuid
from typing import Any

from sqlmodel import Session, col, select

from src.modules.shared.domain.entities.evaluation_run_entity import EvaluationRunEntity
from src.modules.shared.infrastructure.models import EvaluationRunModel


class EvaluationRepository:
    """Story 26.5: the business evaluation runs of generations."""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self, generation_id: str, trigger: str, provider: str | None, expectations_from: str | None = None
    ) -> EvaluationRunEntity:
        model = EvaluationRunModel(
            generation_id=generation_id, trigger=trigger, provider=provider, expectations_from=expectations_from
        )
        self.session.add(model)
        self.session.flush()
        return self._entity(model)

    def update(self, run_id: uuid.UUID, **fields: Any) -> EvaluationRunEntity:
        model = self.session.get(EvaluationRunModel, run_id)
        for key, value in fields.items():
            setattr(model, key, value)
        self.session.flush()
        return self._entity(model)

    def find(self, run_id: uuid.UUID) -> EvaluationRunEntity | None:
        model = self.session.get(EvaluationRunModel, run_id)
        return self._entity(model) if model is not None else None

    def latest(self, generation_id: str) -> EvaluationRunEntity | None:
        statement = (
            select(EvaluationRunModel)
            .where(EvaluationRunModel.generation_id == generation_id)
            .order_by(col(EvaluationRunModel.created_at).desc())
            .limit(1)
        )
        model = self.session.exec(statement).first()
        return self._entity(model) if model is not None else None

    @staticmethod
    def _entity(model: EvaluationRunModel) -> EvaluationRunEntity:
        return EvaluationRunEntity.model_validate(model.model_dump())
