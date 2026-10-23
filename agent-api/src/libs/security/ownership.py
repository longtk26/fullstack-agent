from src.libs.exceptions import NotFoundException


def ensure_owner(owner_id, user_id, is_admin: bool = False, resource: str = "Resource") -> None:
    """Another user's resource is reported as missing (404), not forbidden, so its existence is not leaked."""
    if not is_admin and owner_id != user_id:
        raise NotFoundException(f"{resource} not found")
