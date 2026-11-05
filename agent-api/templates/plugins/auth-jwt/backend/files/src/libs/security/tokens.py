import datetime as dt
from typing import Any

import jwt

from src.configs import config

ALGORITHM = "HS256"


def create_access_token(subject: object, role: str | None = None) -> str:
    """A signed bearer token for `subject` (the user's id), expiring after ACCESS_TOKEN_EXPIRE_MINUTES."""
    now = dt.datetime.now(dt.UTC)
    claims: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": now + dt.timedelta(minutes=config.access_token_expire_minutes),
    }
    if role is not None:
        claims["role"] = role
    return jwt.encode(claims, config.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """The token's claims, or None when it is malformed, forged or expired."""
    try:
        return jwt.decode(token, config.jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
