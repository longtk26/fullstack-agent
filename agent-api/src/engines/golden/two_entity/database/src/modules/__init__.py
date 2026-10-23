"""Imports every ORM model so Alembic autogenerate discovers it (fastapi-skills pillar 4)."""

from src.modules.shared.infrastructure.models import ProjectModel, TaskModel

__all__ = ["ProjectModel", "TaskModel"]
