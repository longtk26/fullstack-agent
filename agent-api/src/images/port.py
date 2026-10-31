"""Port and data types for AI photo generation (Story 19.2)."""

from dataclasses import dataclass
from typing import Protocol


class ImageError(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class ImageBlocked(ImageError):
    """Refused or filtered by safety policies."""


class ImageFailed(ImageError):
    """Network failure, timeout, HTTP 5xx, or unexpected response."""


@dataclass
class GeneratedImage:
    data: bytes
    mime: str
    model: str
    duration_ms: int
    cost_usd: float


class IImageGenerator(Protocol):
    async def generate(self, prompt: str, aspect_ratio: str) -> GeneratedImage: ...
