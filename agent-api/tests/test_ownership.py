import uuid

import pytest

from src.libs.exceptions import NotFoundException
from src.libs.security import ensure_owner

OWNER = uuid.uuid4()
OTHER = uuid.uuid4()


def test_owner_passes():
    ensure_owner(OWNER, OWNER)


def test_other_user_gets_not_found_instead_of_forbidden():
    with pytest.raises(NotFoundException) as exc:
        ensure_owner(OWNER, OTHER, resource="Generation")

    assert exc.value.status_code == 404
    assert exc.value.detail == "Generation not found"


def test_admin_passes_for_any_owner():
    ensure_owner(OWNER, OTHER, is_admin=True)
