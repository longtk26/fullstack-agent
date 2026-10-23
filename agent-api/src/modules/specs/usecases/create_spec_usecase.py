import uuid
from typing import Annotated

from fastapi import Depends
from pydantic import BaseModel

from src.libs.decorators.transactional_decorator import Transactional
from src.libs.exceptions import ErrorCode, UnprocessableEntityException
from src.modules.shared.domain.backend_spec import SpecIssue, validate_spec_text
from src.modules.shared.domain.entities import BackendSpecEntity
from src.modules.shared.domain.enums import SpecSource
from src.modules.specs.ports.output import IBackendSpecRepoDep


class CreatedSpec(BaseModel):
    spec: BackendSpecEntity
    warnings: list[SpecIssue]


class CreateSpecUsecase:
    def __init__(self, spec_repo: IBackendSpecRepoDep):
        self.spec_repo = spec_repo

    @Transactional
    async def execute(self, raw: bytes, owner_id: uuid.UUID, source: SpecSource = SpecSource.JSON) -> CreatedSpec:
        result = validate_spec_text(raw)
        if not result.report.valid:
            raise UnprocessableEntityException(
                "BackendSpec is invalid",
                code=ErrorCode.SPEC_INVALID,
                details=[issue.model_dump(mode="json") for issue in result.report.errors],
            )
        spec = self.spec_repo.create(
            BackendSpecEntity(
                owner_id=owner_id,
                spec_version=result.report.spec_version,
                raw_json=raw.decode("utf-8"),
                normalized_json=result.normalized,
                source=source,
            )
        )
        return CreatedSpec(spec=spec, warnings=result.report.warnings)


CreateSpecUsecaseDep = Annotated[CreateSpecUsecase, Depends(CreateSpecUsecase)]
