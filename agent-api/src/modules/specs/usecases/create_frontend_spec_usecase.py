import uuid
from typing import Annotated

from fastapi import Depends
from pydantic import BaseModel

from src.libs.decorators.transactional_decorator import Transactional
from src.libs.exceptions import ErrorCode, UnprocessableEntityException
from src.modules.shared.domain.backend_spec import SpecIssue
from src.modules.shared.domain.entities import FrontendSpecEntity
from src.modules.shared.domain.enums import SpecSource
from src.modules.shared.domain.frontend_spec import validate_frontend_spec_text
from src.modules.specs.ports.output import IFrontendSpecRepoDep


class CreatedFrontendSpec(BaseModel):
    spec: FrontendSpecEntity
    warnings: list[SpecIssue]


class CreateFrontendSpecUsecase:
    def __init__(self, spec_repo: IFrontendSpecRepoDep):
        self.spec_repo = spec_repo

    @Transactional
    async def execute(
        self, raw: bytes, owner_id: uuid.UUID, source: SpecSource = SpecSource.JSON
    ) -> CreatedFrontendSpec:
        result = validate_frontend_spec_text(raw)
        if not result.report.valid:
            raise UnprocessableEntityException(
                "FrontendSpec is invalid",
                code=ErrorCode.SPEC_INVALID,
                details=[issue.model_dump(mode="json") for issue in result.report.errors],
            )
        spec = self.spec_repo.create(
            FrontendSpecEntity(
                owner_id=owner_id,
                spec_version=result.report.spec_version,
                mode=result.normalized["project"]["mode"],
                raw_json=raw.decode("utf-8"),
                normalized_json=result.normalized,
                source=source,
            )
        )
        return CreatedFrontendSpec(spec=spec, warnings=result.report.warnings)


CreateFrontendSpecUsecaseDep = Annotated[CreateFrontendSpecUsecase, Depends(CreateFrontendSpecUsecase)]
