from fastapi import APIRouter, File, Response, UploadFile, status
from fastapi.responses import FileResponse

from src.configs import config
from src.modules.auth.presenter import CurrentUserDep
from src.modules.uploads.presenter.dtos import UploadDto, UploadListDto
from src.modules.uploads.usecases import CreateUploadUsecaseDep, UploadQueriesDep, upload_file

upload_router = APIRouter(prefix="/api/v1/uploads", tags=["uploads"])
MB = 1024 * 1024


@upload_router.post("", response_model=UploadDto, status_code=status.HTTP_201_CREATED)
async def create_upload(
    user: CurrentUserDep, usecase: CreateUploadUsecaseDep, response: Response, file: UploadFile = File(...)
) -> UploadDto:
    """Story 15.4: one PNG, JPEG, WebP or SVG for generated sites; the same file again returns its upload (200)."""
    data = await file.read(config.upload_max_mb * MB + 1)  # one byte over the limit is enough to refuse it
    upload, created = await usecase.execute(user, file.filename or "upload", data)
    if not created:
        response.status_code = status.HTTP_200_OK
    return UploadDto.from_entity(upload)


@upload_router.get("", response_model=UploadListDto)
async def list_uploads(user: CurrentUserDep, queries: UploadQueriesDep) -> UploadListDto:
    uploads = await queries.list(user)
    return UploadListDto(
        uploads=[UploadDto.from_entity(upload) for upload in uploads],
        used_bytes=sum(upload.bytes for upload in uploads),
        quota_bytes=config.upload_quota_mb * MB,
    )


@upload_router.get("/{upload_id}/content", response_class=FileResponse)
async def upload_content(upload_id: str, user: CurrentUserDep, queries: UploadQueriesDep) -> FileResponse:
    upload = await queries.get(upload_id, user)
    # SVGs are served as files to download-or-<img>, never as a document that could run (they are checked anyway).
    headers = {
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'",
        "X-Content-Type-Options": "nosniff",
    }
    return FileResponse(upload_file(upload), media_type=upload.mime, headers=headers)


@upload_router.delete("/{upload_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_upload(upload_id: str, user: CurrentUserDep, queries: UploadQueriesDep) -> Response:
    await queries.delete(upload_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
