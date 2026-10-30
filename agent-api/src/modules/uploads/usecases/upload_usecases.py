"""Uploads (Story 15.4): a user's images for generated sites, checked and stored under ARTIFACT_ROOT."""

import hashlib
from pathlib import Path
from typing import Annotated

from fastapi import Depends

from src.configs import config
from src.configs.config import uploads_dir
from src.libs.decorators.transactional_decorator import Transactional
from src.libs.exceptions import (
    BadRequestException,
    ErrorCode,
    NotFoundException,
    PayloadTooLargeException,
    UnprocessableEntityException,
)
from src.libs.ids.ulid import new_upload_id
from src.libs.security import ensure_owner
from src.modules.shared.domain.entities import UploadEntity, UserEntity
from src.modules.uploads.infrastructure.adapters.image_processor import UploadRejected, process
from src.modules.uploads.ports.output import IUploadRepoDep

MB = 1024 * 1024


def upload_file(upload: UploadEntity) -> Path:
    return Path(uploads_dir()) / upload.relative_path


class CreateUploadUsecase:
    def __init__(self, uploads: IUploadRepoDep):
        self.uploads = uploads

    @Transactional
    async def execute(self, user: UserEntity, filename: str, data: bytes) -> tuple[UploadEntity, bool]:
        """(upload, created): the same content uploaded again returns the existing upload."""
        if not data:
            raise BadRequestException("The file is empty", code=ErrorCode.BAD_REQUEST)
        if len(data) > config.upload_max_mb * MB:
            raise PayloadTooLargeException(
                f"Files are limited to {config.upload_max_mb} MB",
                code=ErrorCode.PAYLOAD_TOO_LARGE,
                details={"limitMb": config.upload_max_mb, "bytes": len(data)},
            )
        sha256 = hashlib.sha256(data).hexdigest()
        existing = self.uploads.find_by_sha256(user.id, sha256)
        if existing is not None:
            return existing, False
        try:
            image = process(data)
        except UploadRejected as exc:
            code = ErrorCode.UPLOAD_UNSAFE if exc.reason == "unsafe" else ErrorCode.UPLOAD_TYPE_UNSUPPORTED
            raise UnprocessableEntityException(str(exc), code=code) from exc
        used = self.uploads.total_bytes(user.id)
        if used + len(image.content) > config.upload_quota_mb * MB:
            raise PayloadTooLargeException(
                f"Your uploads are limited to {config.upload_quota_mb} MB in total",
                code=ErrorCode.UPLOAD_QUOTA_EXCEEDED,
                details={"quotaMb": config.upload_quota_mb, "usedBytes": used},
            )
        upload = UploadEntity(
            id=new_upload_id(),
            owner_id=user.id,
            filename=Path(filename or "upload").name[:255],
            mime=image.mime,
            bytes=len(image.content),
            width=image.width,
            height=image.height,
            sha256=sha256,
        )
        target = upload_file(upload)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(image.content)
        return self.uploads.create(upload), True


class UploadQueries:
    def __init__(self, uploads: IUploadRepoDep):
        self.uploads = uploads

    async def list(self, user: UserEntity) -> list[UploadEntity]:
        return self.uploads.list_for_owner(user.id)

    async def get(self, upload_id: str, user: UserEntity) -> UploadEntity:
        upload = self.uploads.find(upload_id)
        if upload is None:
            raise NotFoundException("Upload not found")
        ensure_owner(upload.owner_id, user.id, user.is_admin, "Upload")
        return upload

    @Transactional
    async def delete(self, upload_id: str, user: UserEntity) -> None:
        upload = await self.get(upload_id, user)
        self.uploads.delete(upload.id)
        upload_file(upload).unlink(missing_ok=True)


CreateUploadUsecaseDep = Annotated[CreateUploadUsecase, Depends(CreateUploadUsecase)]
UploadQueriesDep = Annotated[UploadQueries, Depends(UploadQueries)]
