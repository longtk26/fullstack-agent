from .preview_repository import IPreviewRepository

_DEPS = {"IPreviewRepoDep"}


def __getattr__(name: str):
    # Lazy so that importing persistence first (which imports this package) does not cycle.
    if name in _DEPS:
        from src.modules.previews.infrastructure import persistence

        return getattr(persistence, name)
    raise AttributeError(name)


__all__ = ["IPreviewRepository", "IPreviewRepoDep"]
