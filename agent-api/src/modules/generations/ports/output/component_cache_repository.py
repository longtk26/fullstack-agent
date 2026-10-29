from abc import ABC, abstractmethod

from src.modules.shared.domain.entities import ComponentCacheEntity


class IComponentCacheRepository(ABC):
    """Rows of the component cache (Story 17.3); the cached files live under ARTIFACT_ROOT/cache/components."""

    @abstractmethod
    def find(self, key: str) -> ComponentCacheEntity | None: ...

    @abstractmethod
    def save(self, entry: ComponentCacheEntity) -> ComponentCacheEntity: ...

    @abstractmethod
    def record_hit(self, key: str) -> None: ...

    @abstractmethod
    def evict(self, key: str) -> None: ...

    @abstractmethod
    def purge(self) -> int: ...

    @abstractmethod
    def most_reused(self, limit: int = 10) -> list[ComponentCacheEntity]: ...
