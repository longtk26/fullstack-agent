import uuid
from typing import Annotated, Any

from fastapi import Depends
from sqlmodel import col, select

from src.libs.database.session import SessionDep
from src.modules.previews.ports.output import IPreviewRepository
from src.modules.shared.domain.entities import PreviewEntity
from src.modules.shared.domain.enums import PreviewStatus
from src.modules.shared.infrastructure.models import GenerationModel, PreviewModel


class PreviewRepository(IPreviewRepository):
    def __init__(self, session: SessionDep):
        self.session = session

    def _model(self, generation_id: str, kind: str) -> PreviewModel | None:
        query = select(PreviewModel).where(PreviewModel.generation_id == generation_id, PreviewModel.kind == kind)
        return self.session.exec(query).first()

    def find(self, generation_id: str, kind: str = "backend") -> PreviewEntity | None:
        model = self._model(generation_id, kind)
        return self.__to_entity(model) if model else None

    def upsert(self, generation_id: str, kind: str = "backend", **fields: Any) -> PreviewEntity:
        model = self._model(generation_id, kind) or PreviewModel(generation_id=generation_id, kind=kind)
        for key, value in fields.items():
            setattr(model, key, value)
        self.session.add(model)
        self.session.flush()
        return self.__to_entity(model)

    def delete(self, generation_id: str, kind: str = "backend") -> None:
        model = self._model(generation_id, kind)
        if model is not None:
            self.session.delete(model)
            self.session.flush()

    def list_for_owner(self, owner_id: uuid.UUID | None) -> list[PreviewEntity]:
        query = select(PreviewModel).join(GenerationModel, col(GenerationModel.id) == PreviewModel.generation_id)
        if owner_id is not None:
            query = query.where(GenerationModel.owner_id == owner_id)
        return [self.__to_entity(m) for m in self.session.exec(query.order_by(col(PreviewModel.started_at).desc()))]

    def list_by_status(self, statuses: tuple[PreviewStatus, ...]) -> list[PreviewEntity]:
        query = select(PreviewModel).where(col(PreviewModel.status).in_(statuses))
        return [self.__to_entity(m) for m in self.session.exec(query)]

    def list_all(self) -> list[PreviewEntity]:
        return [self.__to_entity(m) for m in self.session.exec(select(PreviewModel))]

    @staticmethod
    def __to_entity(model: PreviewModel) -> PreviewEntity:
        return PreviewEntity.model_validate(model.model_dump())


IPreviewRepoDep = Annotated[IPreviewRepository, Depends(PreviewRepository)]
