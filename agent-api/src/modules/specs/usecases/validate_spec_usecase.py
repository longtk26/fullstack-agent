from typing import Annotated

from fastapi import Depends

from src.modules.shared.domain.backend_spec import ValidationReport, validate_spec_text


class ValidateSpecUsecase:
    async def execute(self, raw: bytes) -> ValidationReport:
        return validate_spec_text(raw).report


ValidateSpecUsecaseDep = Annotated[ValidateSpecUsecase, Depends(ValidateSpecUsecase)]
