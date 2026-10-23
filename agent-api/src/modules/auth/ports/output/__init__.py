from .user_repository import IUserRepository


def __getattr__(name: str):
    # Lazy so that importing persistence first (which imports this package) does not cycle.
    if name == "IUserRepoDep":
        from src.modules.auth.infrastructure.persistence import IUserRepoDep

        return IUserRepoDep
    raise AttributeError(name)


__all__ = ["IUserRepository", "IUserRepoDep"]
