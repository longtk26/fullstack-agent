from typing import Annotated

from fastapi import Depends

from src.libs.queue import PreviewCommandBus
from src.libs.redis import get_redis


def get_preview_bus() -> PreviewCommandBus:
    return PreviewCommandBus(get_redis())


PreviewCommandBusDep = Annotated[PreviewCommandBus, Depends(get_preview_bus)]

__all__ = ["PreviewCommandBusDep", "get_preview_bus"]
