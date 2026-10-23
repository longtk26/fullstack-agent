from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from src.configs import config


def create_access_token(subject: str, claims: dict[str, Any] | None = None) -> tuple[str, int]:
    expires_in = config.access_token_expire_minutes * 60
    now = datetime.now(UTC)
    payload = {"sub": subject, "iat": now, "exp": now + timedelta(seconds=expires_in), **(claims or {})}
    return jwt.encode(payload, config.jwt_secret, algorithm=config.jwt_algorithm), expires_in


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, config.jwt_secret, algorithms=[config.jwt_algorithm], options={"require": ["sub"]})
    except jwt.PyJWTError:
        return None
