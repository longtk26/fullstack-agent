import os
import time

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def new_ulid() -> str:
    value = (int(time.time() * 1000) << 80) | int.from_bytes(os.urandom(10), "big")
    return "".join(_CROCKFORD[(value >> shift) & 31] for shift in range(125, -1, -5))


def new_generation_id() -> str:
    return f"gen_{new_ulid()}"


def new_artifact_id() -> str:
    return f"art_{new_ulid()}"
