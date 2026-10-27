from typing import Annotated, Any

from fastapi import Depends

from src.libs.exceptions import NotFoundException
from src.modules.shared.domain.frontend_spec import frontend_spec_json_schema, supported_frontend_versions


class GetFrontendSpecSchemaUsecase:
    async def execute(self, version: str) -> dict[str, Any]:
        if version not in supported_frontend_versions():
            raise NotFoundException(
                f"No FrontendSpec schema for version {version!r}", details=supported_frontend_versions()
            )
        return frontend_spec_json_schema(version)


GetFrontendSpecSchemaUsecaseDep = Annotated[GetFrontendSpecSchemaUsecase, Depends(GetFrontendSpecSchemaUsecase)]
