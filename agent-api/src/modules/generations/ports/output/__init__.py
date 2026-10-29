from .artifact_repository import IArtifactRepository
from .component_cache_repository import IComponentCacheRepository
from .execution_record_repository import IExecutionRecordRepository
from .generation_event_repository import IGenerationEventRepository
from .generation_repository import IGenerationRepository

_DEPS = {
    "IArtifactRepoDep",
    "IComponentCacheRepoDep",
    "IGenerationRepoDep",
    "IGenerationEventRepoDep",
    "IExecutionRecordRepoDep",
}


def __getattr__(name: str):
    # Lazy so that importing persistence first (which imports this package) does not cycle.
    if name in _DEPS:
        from src.modules.generations.infrastructure import persistence

        return getattr(persistence, name)
    raise AttributeError(name)


__all__ = [
    "IArtifactRepository",
    "IArtifactRepoDep",
    "IComponentCacheRepository",
    "IComponentCacheRepoDep",
    "IExecutionRecordRepository",
    "IGenerationEventRepository",
    "IGenerationRepository",
    "IExecutionRecordRepoDep",
    "IGenerationEventRepoDep",
    "IGenerationRepoDep",
]
