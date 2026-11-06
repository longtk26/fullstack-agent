from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from src.configs import config, get_logger

from .object_storage import IObjectStorage
from .s3_storage import S3ObjectStorage

logger = get_logger(__name__)


@lru_cache
def get_storage() -> IObjectStorage:
    return S3ObjectStorage(
        endpoint=config.storage_endpoint,
        public_endpoint=config.storage_public_endpoint,
        bucket=config.storage_bucket,
        region=config.storage_region,
        access_key=config.storage_access_key,
        secret_key=config.storage_secret_key,
    )


ObjectStorageDep = Annotated[IObjectStorage, Depends(get_storage)]


def signed_url(key: str | None) -> str | None:
    """A record's file as a URL that reads it (a response field), or None without a file. A seeded record may hold an
    outside URL instead of a key (a demo photo): it is read as it is. Uploads still take keys only (`check_upload`)."""
    if key is None:
        return None
    if key.startswith(("https://", "http://")):
        return key
    return get_storage().signed_url(key, config.storage_url_expire_seconds)


def ensure_bucket() -> None:
    """At startup: the bucket and its CORS rule. A storage that cannot be reached is logged, not fatal."""
    try:
        get_storage().ensure_bucket(config.cors_origin_list)
    except Exception as exc:  # noqa: BLE001 - startup goes on; uploads fail with the storage's own error
        logger.error("object storage unavailable", extra={"error": str(exc)})
