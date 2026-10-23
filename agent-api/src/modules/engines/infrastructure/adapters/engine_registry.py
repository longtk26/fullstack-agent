from typing import Annotated

from fastapi import Depends

from src.engines import EngineHealthStore, EngineRegistry, get_engine_registry
from src.libs.redis import get_redis

EngineRegistryDep = Annotated[EngineRegistry, Depends(get_engine_registry)]


def get_engine_health_store() -> EngineHealthStore:
    return EngineHealthStore(get_redis())


EngineHealthStoreDep = Annotated[EngineHealthStore, Depends(get_engine_health_store)]
