from abc import ABC, abstractmethod

from src.modules.shared.domain.entities import ArtifactEntity


class IArtifactRepository(ABC):
    @abstractmethod
    def replace_for_generation(self, generation_id: str, artifacts: list[ArtifactEntity]) -> None:
        """Rows with the same name are replaced; others are kept (diagnostics written earlier stay listed)."""

    @abstractmethod
    def list_for_generation(self, generation_id: str) -> list[ArtifactEntity]:
        pass

    @abstractmethod
    def find(self, generation_id: str, artifact_id: str) -> ArtifactEntity | None:
        pass

    @abstractmethod
    def find_by_name(self, generation_id: str, name: str) -> ArtifactEntity | None:
        pass
