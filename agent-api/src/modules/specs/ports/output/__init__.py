from .backend_spec_repository import IBackendSpecRepository
from .frontend_spec_repository import IFrontendSpecRepository
from .spec_draft_repository import ISpecDraftRepository


def __getattr__(name: str):
    # Lazy so that importing persistence first (which imports this package) does not cycle.
    if name in ("IBackendSpecRepoDep", "IFrontendSpecRepoDep", "ISpecDraftRepoDep"):
        from src.modules.specs.infrastructure import persistence

        return getattr(persistence, name)
    raise AttributeError(name)


__all__ = [
    "IBackendSpecRepository",
    "IBackendSpecRepoDep",
    "IFrontendSpecRepository",
    "IFrontendSpecRepoDep",
    "ISpecDraftRepository",
    "ISpecDraftRepoDep",
]
