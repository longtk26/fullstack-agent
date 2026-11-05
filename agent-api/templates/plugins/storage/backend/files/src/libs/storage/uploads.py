import re
import uuid
from dataclasses import dataclass
from http import HTTPStatus

from src.libs.exceptions import BadRequestException, ErrorCode
from src.libs.exceptions.base_exception import BaseException as AppException

from .object_storage import IObjectStorage


@dataclass(frozen=True)
class FileRule:
    """A file field: its API name, the MIME types it takes (`image/*` allowed), the largest size and its key prefix."""

    field: str
    accept: tuple[str, ...]
    max_size: int
    prefix: str

    def accepts(self, content_type: str) -> bool:
        kind = content_type.split(";")[0].strip().lower()
        return not self.accept or any(
            kind == allowed or (allowed.endswith("/*") and kind.startswith(allowed[:-1])) for allowed in self.accept
        )


def check_declared(rule: FileRule, content_type: str, size: int) -> None:
    """Before an upload: what the client says it will send."""
    if not rule.accepts(content_type):
        raise AppException(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            f"{rule.field} takes {', '.join(rule.accept)}",
            ErrorCode.FILE_TYPE_NOT_ALLOWED,
            details={"fields": [rule.field], "accept": list(rule.accept)},
        )
    if size > rule.max_size:
        raise AppException(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            f"{rule.field} is at most {rule.max_size} bytes",
            ErrorCode.FILE_TOO_LARGE,
            details={"fields": [rule.field], "maxSize": rule.max_size},
        )


def new_key(rule: FileRule, filename: str, owner: object | None = None) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", filename).strip("-.")[:100] or "file"
    return f"{rule.prefix}/{owner if owner is not None else 'shared'}/{uuid.uuid4().hex}/{safe}"


def check_upload(storage: IObjectStorage, rule: FileRule, key: str, owner: object | None = None) -> None:
    """Before a record keeps a key: it was uploaded for this field (by this user), with an allowed type and size."""
    prefix = f"{rule.prefix}/{owner}/" if owner is not None else f"{rule.prefix}/"
    found = storage.stat(key) if key.startswith(prefix) else None
    if found is None:
        raise BadRequestException(
            f"No file was uploaded for {rule.field} under this key",
            ErrorCode.FILE_NOT_FOUND,
            details={"fields": [rule.field]},
        )
    check_declared(rule, found.content_type, found.size)
