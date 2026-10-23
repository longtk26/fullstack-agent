import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Query, Request, status

from src.configs import config
from src.libs.http import read_body_limited
from src.modules.auth.presenter import CurrentUserDep
from src.modules.shared.domain.backend_spec import LATEST_SPEC_VERSION
from src.modules.shared.domain.enums import SpecSource
from src.modules.specs.presenter.dtos import (
    CreateSpecResponseDto,
    FrontendImportResponseDto,
    GetSpecResponseDto,
    SpecIssueDto,
    ValidationReportDto,
)
from src.modules.specs.usecases import (
    CreateSpecUsecaseDep,
    GetSpecSchemaUsecaseDep,
    GetSpecUsecaseDep,
    ImportFrontendSpecUsecaseDep,
    ValidateSpecUsecaseDep,
)

spec_router = APIRouter(prefix="/api/v1/specs", tags=["specs"])
spec_import_router = APIRouter(prefix="/api/v1/spec-imports", tags=["specs"])

# The body is read raw (to keep the submitted spec byte-for-byte and report malformed JSON ourselves),
# so the request schema is declared for the docs only.
_RAW_JSON_BODY = {"requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object"}}}}}


@spec_router.get("/schema", response_model=dict[str, Any])
async def get_spec_schema(
    _: CurrentUserDep,
    usecase: GetSpecSchemaUsecaseDep,
    version: Annotated[str, Query()] = LATEST_SPEC_VERSION,
) -> dict[str, Any]:
    return await usecase.execute(version)


@spec_router.post("/validate", response_model=ValidationReportDto, openapi_extra=_RAW_JSON_BODY)
async def validate_spec(request: Request, _: CurrentUserDep, usecase: ValidateSpecUsecaseDep) -> ValidationReportDto:
    raw = await read_body_limited(request, config.spec_max_bytes)
    return ValidationReportDto.from_domain(await usecase.execute(raw))


@spec_router.post(
    "",
    response_model=CreateSpecResponseDto,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=_RAW_JSON_BODY,
)
async def create_spec(
    request: Request,
    user: CurrentUserDep,
    usecase: CreateSpecUsecaseDep,
    source: Annotated[SpecSource, Query()] = SpecSource.JSON,
) -> CreateSpecResponseDto:
    raw = await read_body_limited(request, config.spec_max_bytes)
    created = await usecase.execute(raw, user.id, source)
    return CreateSpecResponseDto(
        spec_id=str(created.spec.id),
        spec_version=created.spec.spec_version,
        warnings=[SpecIssueDto.from_domain(issue) for issue in created.warnings],
    )


@spec_router.get("/{spec_id}", response_model=GetSpecResponseDto)
async def get_spec(spec_id: uuid.UUID, user: CurrentUserDep, usecase: GetSpecUsecaseDep) -> GetSpecResponseDto:
    return GetSpecResponseDto.from_entity(await usecase.execute(spec_id, user))


@spec_import_router.post("/frontend", response_model=FrontendImportResponseDto, openapi_extra=_RAW_JSON_BODY)
async def import_frontend_spec(
    request: Request,
    _: CurrentUserDep,
    usecase: ImportFrontendSpecUsecaseDep,
    include_admin_crud: Annotated[bool, Query(alias="includeAdminCrud")] = True,
) -> FrontendImportResponseDto:
    raw = await read_body_limited(request, config.frontend_import_max_bytes)
    return FrontendImportResponseDto.from_domain(await usecase.execute(raw, include_admin_crud))
