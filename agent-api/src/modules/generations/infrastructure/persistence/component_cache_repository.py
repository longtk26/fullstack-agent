from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from sqlmodel import delete, select, update

from src.libs.database.session import SessionDep
from src.modules.generations.ports.output.component_cache_repository import IComponentCacheRepository
from src.modules.shared.domain.entities import ComponentCacheEntity
from src.modules.shared.infrastructure.models import ComponentCacheModel


class ComponentCacheRepository(IComponentCacheRepository):
    def __init__(self, session: SessionDep):
        self.session = session

    def find(self, key: str) -> ComponentCacheEntity | None:
        model = self.session.get(ComponentCacheModel, key)
        return ComponentCacheEntity.model_validate(model.model_dump()) if model else None

    def save(self, entry: ComponentCacheEntity) -> ComponentCacheEntity:
        """A new entry, or a regenerated one (after an eviction or a lost file): its hits start again."""
        model = self.session.get(ComponentCacheModel, entry.key) or ComponentCacheModel(key=entry.key)
        for field, value in entry.model_dump(exclude={"key", "created_at", "last_used_at"}).items():
            setattr(model, field, value)
        model.created_at = model.last_used_at = datetime.now(UTC)
        self.session.add(model)
        self.session.flush()
        return ComponentCacheEntity.model_validate(model.model_dump())

    def record_hit(self, key: str) -> None:
        statement = (
            update(ComponentCacheModel)
            .where(ComponentCacheModel.key == key)
            .values(hits=ComponentCacheModel.hits + 1, last_used_at=datetime.now(UTC))
        )
        self.session.exec(statement)  # one statement: concurrent hits all count

    def evict(self, key: str) -> None:
        self.session.exec(delete(ComponentCacheModel).where(ComponentCacheModel.key == key))

    def purge(self) -> int:
        return self.session.exec(delete(ComponentCacheModel)).rowcount or 0

    def most_reused(self, limit: int = 10) -> list[ComponentCacheEntity]:
        statement = (
            select(ComponentCacheModel)
            .where(ComponentCacheModel.hits > 0)
            .order_by(ComponentCacheModel.hits.desc(), ComponentCacheModel.key)
            .limit(limit)
        )
        return [ComponentCacheEntity.model_validate(m.model_dump()) for m in self.session.exec(statement)]


IComponentCacheRepoDep = Annotated[IComponentCacheRepository, Depends(ComponentCacheRepository)]
