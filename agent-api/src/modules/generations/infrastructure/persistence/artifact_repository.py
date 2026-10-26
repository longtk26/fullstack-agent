from typing import Annotated

from fastapi import Depends
from sqlmodel import col, delete, select

from src.libs.database.session import SessionDep
from src.modules.generations.ports.output import IArtifactRepository
from src.modules.shared.domain.entities import ArtifactEntity
from src.modules.shared.infrastructure.models import ArtifactModel


class ArtifactRepository(IArtifactRepository):
    def __init__(self, session: SessionDep):
        self.session = session

    def replace_for_generation(self, generation_id: str, artifacts: list[ArtifactEntity]) -> None:
        names = [artifact.name for artifact in artifacts]
        self.session.exec(
            delete(ArtifactModel).where(
                ArtifactModel.generation_id == generation_id, col(ArtifactModel.name).in_(names)
            )
        )
        for artifact in artifacts:
            self.session.add(ArtifactModel(**artifact.model_dump(exclude_none=True)))
        self.session.flush()

    def list_for_generation(self, generation_id: str) -> list[ArtifactEntity]:
        query = select(ArtifactModel).where(ArtifactModel.generation_id == generation_id)
        models = self.session.exec(query.order_by(ArtifactModel.kind, ArtifactModel.name))
        return [ArtifactEntity.model_validate(model.model_dump()) for model in models]

    def find(self, generation_id: str, artifact_id: str) -> ArtifactEntity | None:
        model = self.session.get(ArtifactModel, artifact_id)
        if model is None or model.generation_id != generation_id:
            return None
        return ArtifactEntity.model_validate(model.model_dump())

    def find_by_name(self, generation_id: str, name: str) -> ArtifactEntity | None:
        query = select(ArtifactModel).where(ArtifactModel.generation_id == generation_id, ArtifactModel.name == name)
        model = self.session.exec(query).first()
        return ArtifactEntity.model_validate(model.model_dump()) if model else None


IArtifactRepoDep = Annotated[IArtifactRepository, Depends(ArtifactRepository)]
