import uuid
from datetime import datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Text, cast, exists, func
from sqlmodel import Session, col, select

from src.libs.database.session import SessionDep
from src.modules.shared.domain.entities import UploadEntity
from src.modules.shared.infrastructure.models import FrontendSpecModel, SpecDraftModel, UploadModel
from src.modules.uploads.ports.output import IUploadRepository


class UploadRepository(IUploadRepository):
    def __init__(self, session: SessionDep):
        self.session: Session = session

    def create(self, upload: UploadEntity) -> UploadEntity:
        model = UploadModel(**upload.model_dump(exclude_none=True))
        self.session.add(model)
        self.session.flush()
        return self.__to_entity(model)

    def find(self, upload_id: str) -> UploadEntity | None:
        model = self.session.get(UploadModel, upload_id)
        return self.__to_entity(model) if model else None

    def find_by_sha256(self, owner_id: uuid.UUID, sha256: str) -> UploadEntity | None:
        model = self.session.exec(
            select(UploadModel).where(UploadModel.owner_id == owner_id, UploadModel.sha256 == sha256)
        ).first()
        return self.__to_entity(model) if model else None

    def list_for_owner(self, owner_id: uuid.UUID) -> list[UploadEntity]:
        rows = self.session.exec(
            select(UploadModel).where(UploadModel.owner_id == owner_id).order_by(col(UploadModel.created_at).desc())
        ).all()
        return [self.__to_entity(row) for row in rows]

    def total_bytes(self, owner_id: uuid.UUID) -> int:
        total = self.session.exec(
            select(func.coalesce(func.sum(UploadModel.bytes), 0)).where(UploadModel.owner_id == owner_id)
        ).one()
        return int(total)

    def delete(self, upload_id: str) -> None:
        model = self.session.get(UploadModel, upload_id)
        if model is not None:
            self.session.delete(model)
            self.session.flush()

    def unreferenced_before(self, created_before: datetime) -> list[UploadEntity]:
        # A saved FrontendSpec or an existing draft names it (Story 19.3).
        used_in_specs = exists().where(col(FrontendSpecModel.raw_json).contains(func.concat("upload:", UploadModel.id)))
        used_in_drafts = exists().where(
            cast(SpecDraftModel.frontend_spec, Text).contains(func.concat("upload:", UploadModel.id))
        )
        rows = self.session.exec(
            select(UploadModel).where(UploadModel.created_at < created_before, ~used_in_specs, ~used_in_drafts)
        ).all()
        return [self.__to_entity(row) for row in rows]

    @staticmethod
    def __to_entity(model: UploadModel) -> UploadEntity:
        return UploadEntity.model_validate(model, from_attributes=True)


IUploadRepoDep = Annotated[IUploadRepository, Depends(UploadRepository)]
