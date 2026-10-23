from typing import Annotated, Any

from fastapi import Depends

from src.libs.exceptions import NotFoundException
from src.modules.shared.domain.backend_spec import spec_json_schema, supported_versions


class GetSpecSchemaUsecase:
    async def execute(self, version: str) -> dict[str, Any]:
        if version not in supported_versions():
            raise NotFoundException(f"No BackendSpec schema for version {version!r}", details=supported_versions())
        return spec_json_schema(version)


GetSpecSchemaUsecaseDep = Annotated[GetSpecSchemaUsecase, Depends(GetSpecSchemaUsecase)]
