from typing import Annotated

from fastapi import Depends
from sqlalchemy import func
from sqlmodel import col, select

from src.libs.database.session import SessionDep
from src.modules.generations.ports.output import IGenerationEventRepository
from src.modules.shared.domain.entities import GenerationEventEntity
from src.modules.shared.infrastructure.models import GenerationEventModel


class GenerationEventRepository(IGenerationEventRepository):
    def __init__(self, session: SessionDep):
        self.session = session

    def append(self, event: GenerationEventEntity) -> GenerationEventEntity:
        model = GenerationEventModel(**event.model_dump(exclude_none=True))
        self.session.add(model)
        self.session.flush()
        return GenerationEventEntity.model_validate(model.model_dump())

    def list_after(self, generation_id: str, after_id: int, limit: int = 1000) -> list[GenerationEventEntity]:
        query = (
            select(GenerationEventModel)
            .where(GenerationEventModel.generation_id == generation_id, col(GenerationEventModel.id) > after_id)
            .order_by(col(GenerationEventModel.id))
            .limit(limit)
        )
        return [GenerationEventEntity.model_validate(m.model_dump()) for m in self.session.exec(query)]

    def count(self, generation_id: str) -> int:
        query = select(func.count()).where(GenerationEventModel.generation_id == generation_id)
        return self.session.exec(query).one()


IGenerationEventRepoDep = Annotated[IGenerationEventRepository, Depends(GenerationEventRepository)]
