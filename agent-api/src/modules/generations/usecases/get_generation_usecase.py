from typing import Annotated

from fastapi import Depends
from pydantic import BaseModel

from src.libs.exceptions import NotFoundException
from src.libs.security import ensure_owner
from src.modules.generations.ports.output import IArtifactRepoDep, IExecutionRecordRepoDep, IGenerationRepoDep
from src.modules.previews.ports.output import IPreviewRepoDep
from src.modules.shared.domain.entities import (
    ArtifactEntity,
    CliInvocationEntity,
    GenerationEntity,
    NodeRunEntity,
    PreviewEntity,
    UserEntity,
)
from src.modules.specs.ports.output import IBackendSpecRepoDep, IFrontendSpecRepoDep

from .project_names import project_names


class GenerationDetail(BaseModel):
    generation: GenerationEntity
    project_name: str | None
    validation: dict[str, str]
    steps: list[NodeRunEntity]
    invocations: list[CliInvocationEntity]
    artifacts: list[ArtifactEntity] = []
    preview: PreviewEntity | None = None
    frontend_preview: PreviewEntity | None = None


class GetGenerationUsecase:
    def __init__(
        self,
        generation_repo: IGenerationRepoDep,
        records: IExecutionRecordRepoDep,
        spec_repo: IBackendSpecRepoDep,
        frontend_spec_repo: IFrontendSpecRepoDep,
        artifact_repo: IArtifactRepoDep,
        preview_repo: IPreviewRepoDep,
    ):
        self.frontend_spec_repo = frontend_spec_repo
        self.generation_repo = generation_repo
        self.records = records
        self.spec_repo = spec_repo
        self.artifact_repo = artifact_repo
        self.preview_repo = preview_repo

    def load(self, generation_id: str, user: UserEntity) -> GenerationEntity:
        generation = self.generation_repo.find_by_id(generation_id)
        if generation is None:
            raise NotFoundException("Generation not found")
        ensure_owner(generation.owner_id, user.id, user.is_admin, resource="Generation")
        return generation

    async def execute(self, generation_id: str, user: UserEntity) -> GenerationDetail:
        generation = self.load(generation_id, user)
        validation: dict[str, str] = {}
        for run in self.records.list_validation_runs(generation_id):  # oldest first, so the latest attempt wins
            validation[run.check] = run.status
        return GenerationDetail(
            generation=generation,
            project_name=project_names([generation], self.spec_repo, self.frontend_spec_repo)[generation.id],
            validation=validation,
            steps=self.records.list_node_runs(generation_id),
            invocations=self.records.list_cli_invocations(generation_id),
            artifacts=self.artifact_repo.list_for_generation(generation_id),
            preview=self.preview_repo.find(generation_id),
            frontend_preview=self.preview_repo.find(generation_id, "frontend"),
        )


GetGenerationUsecaseDep = Annotated[GetGenerationUsecase, Depends(GetGenerationUsecase)]
