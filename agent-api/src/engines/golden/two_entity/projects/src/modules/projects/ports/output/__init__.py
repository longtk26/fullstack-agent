from .project_repository import IProjectRepository  # noqa: I001  (must load before the implementation)
from src.modules.projects.infrastructure.persistence import IProjectRepoDep

__all__ = ["IProjectRepository", "IProjectRepoDep"]
