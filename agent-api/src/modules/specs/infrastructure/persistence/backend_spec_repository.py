import uuid
from typing import Annotated

from fastapi import Depends
from sqlmodel import col, select

from src.libs.database.session import SessionDep
from src.modules.shared.domain.entities import BackendSpecEntity
from src.modules.shared.domain.enums import SpecSource
from src.modules.shared.infrastructure.models import BackendSpecModel
from src.modules.specs.ports.output import IBackendSpecRepository


class BackendSpecRepository(IBackendSpecRepository):
    def __init__(self, session: SessionDep):
        self.session = session

    def create(self, spec: BackendSpecEntity) -> BackendSpecEntity:
        model = self.__to_model(spec)
        self.session.add(model)
        self.session.flush()
        return self.__to_entity(model)

    def find_by_id(self, spec_id: uuid.UUID) -> BackendSpecEntity | None:
        model = self.session.get(BackendSpecModel, spec_id)
        return self.__to_entity(model) if model else None

    def find_by_ids(self, spec_ids: list[uuid.UUID]) -> dict[uuid.UUID, BackendSpecEntity]:
        if not spec_ids:
            return {}
        query = select(BackendSpecModel).where(col(BackendSpecModel.id).in_(spec_ids))
        return {model.id: self.__to_entity(model) for model in self.session.exec(query)}

    def __to_entity(self, model: BackendSpecModel) -> BackendSpecEntity:
        return BackendSpecEntity(
            id=model.id,
            owner_id=model.owner_id,
            spec_version=model.spec_version,
            raw_json=model.raw_json,
            normalized_json=model.normalized_json,
            source=SpecSource(model.source),
            requirement_text=model.requirement_text,
            created_at=model.created_at,
        )

    def __to_model(self, entity: BackendSpecEntity) -> BackendSpecModel:
        return BackendSpecModel(
            owner_id=entity.owner_id,
            spec_version=entity.spec_version,
            raw_json=entity.raw_json,
            normalized_json=entity.normalized_json,
            source=entity.source,
            requirement_text=entity.requirement_text,
        )


IBackendSpecRepoDep = Annotated[IBackendSpecRepository, Depends(BackendSpecRepository)]
