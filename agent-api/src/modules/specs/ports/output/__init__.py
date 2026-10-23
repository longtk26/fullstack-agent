from .backend_spec_repository import IBackendSpecRepository


def __getattr__(name: str):
    # Lazy so that importing persistence first (which imports this package) does not cycle.
    if name == "IBackendSpecRepoDep":
        from src.modules.specs.infrastructure.persistence import IBackendSpecRepoDep

        return IBackendSpecRepoDep
    raise AttributeError(name)


__all__ = ["IBackendSpecRepository", "IBackendSpecRepoDep"]
