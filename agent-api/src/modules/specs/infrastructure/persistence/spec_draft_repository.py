import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import Depends
from sqlmodel import col, select, update

from src.libs.database.session import SessionDep
from src.modules.shared.domain.entities import SpecDraftEntity
from src.modules.shared.domain.enums import SpecDraftStatus
from src.modules.shared.infrastructure.models import SpecDraftModel
from src.modules.shared.infrastructure.models._columns import utcnow
from src.modules.specs.ports.output import ISpecDraftRepository


class SpecDraftRepository(ISpecDraftRepository):
    def __init__(self, session: SessionDep):
        self.session = session

    def create(self, draft: SpecDraftEntity) -> SpecDraftEntity:
        model = SpecDraftModel(**draft.model_dump(exclude_none=True, exclude={"id", "created_at", "updated_at"}))
        self.session.add(model)
        self.session.flush()
        return self.__to_entity(model)

    def find_by_id(self, draft_id: uuid.UUID) -> SpecDraftEntity | None:
        model = self.session.get(SpecDraftModel, draft_id)
        return self.__to_entity(model) if model else None

    def update(self, draft_id: uuid.UUID, **fields: Any) -> SpecDraftEntity:
        model = self.session.get(SpecDraftModel, draft_id)
        for key, value in fields.items():
            setattr(model, key, value)
        model.updated_at = utcnow()
        self.session.flush()
        return self.__to_entity(model)

    def claim(self, draft_id: uuid.UUID, worker_id: str) -> SpecDraftEntity | None:
        now = utcnow()
        claimed = self.session.exec(
            update(SpecDraftModel)
            .where(col(SpecDraftModel.id) == draft_id, col(SpecDraftModel.status) == SpecDraftStatus.PENDING)
            .values(status=SpecDraftStatus.RUNNING, worker_id=worker_id, started_at=now, updated_at=now)
        )
        if claimed.rowcount != 1:
            return None
        self.session.flush()
        return self.find_by_id(draft_id)

    def find_stale_running(self, updated_before: datetime) -> list[SpecDraftEntity]:
        query = select(SpecDraftModel).where(
            col(SpecDraftModel.status).in_([SpecDraftStatus.PENDING, SpecDraftStatus.RUNNING]),
            col(SpecDraftModel.updated_at) < updated_before,
        )
        return [self.__to_entity(model) for model in self.session.exec(query)]

    def list_created_between(
        self, owner_id: uuid.UUID | None, start: datetime, end: datetime, limit: int
    ) -> list[SpecDraftEntity]:
        query = select(SpecDraftModel).where(SpecDraftModel.created_at >= start, SpecDraftModel.created_at < end)
        if owner_id is not None:
            query = query.where(SpecDraftModel.owner_id == owner_id)
        query = query.order_by(col(SpecDraftModel.created_at).desc()).limit(limit)
        return [self.__to_entity(model) for model in self.session.exec(query)]

    def __to_entity(self, model: SpecDraftModel) -> SpecDraftEntity:
        return SpecDraftEntity.model_validate(model.model_dump())


ISpecDraftRepoDep = Annotated[ISpecDraftRepository, Depends(SpecDraftRepository)]
