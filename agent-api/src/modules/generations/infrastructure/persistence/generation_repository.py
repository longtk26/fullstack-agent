from datetime import datetime
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import and_, or_
from sqlmodel import col, select

from src.libs.database.session import SessionDep
from src.modules.generations.ports.output import IGenerationRepository
from src.modules.shared.domain.entities import GenerationEntity
from src.modules.shared.domain.enums import GenerationStatus
from src.modules.shared.infrastructure.models import GenerationModel

ACTIVE = (GenerationStatus.RUNNING, GenerationStatus.VALIDATING, GenerationStatus.REPAIRING)
TERMINAL = (GenerationStatus.COMPLETED, GenerationStatus.FAILED, GenerationStatus.CANCELLED)


class GenerationRepository(IGenerationRepository):
    def __init__(self, session: SessionDep):
        self.session = session

    def create(self, generation: GenerationEntity) -> GenerationEntity:
        model = GenerationModel(**generation.model_dump(exclude_none=True))
        self.session.add(model)
        self.session.flush()
        return self.__to_entity(model)

    def find_by_id(self, generation_id: str) -> GenerationEntity | None:
        model = self.session.get(GenerationModel, generation_id)
        return self.__to_entity(model) if model else None

    def update(self, generation_id: str, **fields: Any) -> GenerationEntity:
        model = self.session.get(GenerationModel, generation_id)
        for key, value in fields.items():
            setattr(model, key, value)
        self.session.flush()
        return self.__to_entity(model)

    def list_page(self, owner_id, status, before, limit) -> list[GenerationEntity]:
        query = select(GenerationModel)
        if owner_id is not None:
            query = query.where(GenerationModel.owner_id == owner_id)
        if status is not None:
            query = query.where(GenerationModel.status == status)
        if before is not None:
            created_at, last_id = before
            query = query.where(
                or_(
                    col(GenerationModel.created_at) < created_at,
                    and_(GenerationModel.created_at == created_at, col(GenerationModel.id) < last_id),
                )
            )
        query = query.order_by(col(GenerationModel.created_at).desc(), col(GenerationModel.id).desc()).limit(limit)
        return [self.__to_entity(model) for model in self.session.exec(query)]

    def find_stale_active(self, heartbeat_before: datetime) -> list[GenerationEntity]:
        query = select(GenerationModel).where(
            col(GenerationModel.status).in_(ACTIVE),
            or_(col(GenerationModel.heartbeat_at).is_(None), col(GenerationModel.heartbeat_at) < heartbeat_before),
        )
        return [self.__to_entity(model) for model in self.session.exec(query)]

    def find_pending_created_before(self, created_before: datetime) -> list[GenerationEntity]:
        query = select(GenerationModel).where(
            GenerationModel.status == GenerationStatus.PENDING, col(GenerationModel.created_at) < created_before
        )
        return [self.__to_entity(model) for model in self.session.exec(query)]

    def find_finished_before(self, finished_before: datetime) -> list[str]:
        query = select(GenerationModel.id).where(
            col(GenerationModel.status).in_(TERMINAL), col(GenerationModel.finished_at) < finished_before
        )
        return list(self.session.exec(query))

    def list_created_between(self, owner_id, start, end, limit) -> list[GenerationEntity]:
        query = select(GenerationModel).where(
            col(GenerationModel.created_at) >= start, col(GenerationModel.created_at) < end
        )
        if owner_id is not None:
            query = query.where(GenerationModel.owner_id == owner_id)
        query = query.order_by(col(GenerationModel.created_at).desc()).limit(limit)
        return [self.__to_entity(model) for model in self.session.exec(query)]

    def __to_entity(self, model: GenerationModel) -> GenerationEntity:
        return GenerationEntity.model_validate(model.model_dump())


IGenerationRepoDep = Annotated[IGenerationRepository, Depends(GenerationRepository)]
