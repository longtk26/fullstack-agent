from .upload_repository import IUploadRepository


def __getattr__(name: str):
    # Lazy so that importing persistence first (which imports this package) does not cycle.
    if name == "IUploadRepoDep":
        from src.modules.uploads.infrastructure import persistence

        return getattr(persistence, name)
    raise AttributeError(name)


__all__ = ["IUploadRepository", "IUploadRepoDep"]
