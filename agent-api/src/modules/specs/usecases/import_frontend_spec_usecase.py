import json
from typing import Annotated

from fastapi import Depends

from src.libs.exceptions import BadRequestException, ErrorCode
from src.modules.shared.domain.frontend_site import FrontendImportError, FrontendImportResult, import_frontend_site


class ImportFrontendSpecUsecase:
    async def execute(self, raw: bytes, include_admin_crud: bool = True) -> FrontendImportResult:
        try:
            site = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise BadRequestException(f"Body is not valid JSON: {exc}", code=ErrorCode.JSON_MALFORMED) from exc
        try:
            return import_frontend_site(site, include_admin_crud=include_admin_crud)
        except FrontendImportError as exc:
            raise BadRequestException(str(exc), code=ErrorCode.FRONTEND_JSON_INVALID) from exc


ImportFrontendSpecUsecaseDep = Annotated[ImportFrontendSpecUsecase, Depends(ImportFrontendSpecUsecase)]
