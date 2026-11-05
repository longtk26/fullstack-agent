from abc import ABC, abstractmethod
from typing import NamedTuple


class StoredObject(NamedTuple):
    size: int
    content_type: str


class IObjectStorage(ABC):
    """Where uploaded files live (Story 10.5): an S3-compatible bucket in this app; a fake in a test."""

    @abstractmethod
    def presign_upload(self, key: str, content_type: str, expires_in: int) -> str:
        """A URL a client PUTs the file to, with exactly this `Content-Type`."""

    @abstractmethod
    def signed_url(self, key: str, expires_in: int) -> str:
        """A URL that reads the file until it expires."""

    @abstractmethod
    def stat(self, key: str) -> StoredObject | None:
        """The object's size and type; None when nothing was uploaded under the key."""

    @abstractmethod
    def put(self, key: str, data: bytes, content_type: str) -> None:
        pass

    @abstractmethod
    def ensure_bucket(self, cors_origins: list[str]) -> None:
        """Creates the bucket when it is missing and lets those origins upload and read (browser CORS)."""
