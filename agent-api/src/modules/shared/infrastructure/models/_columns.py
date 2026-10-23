from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import JSONB

TZDateTime = DateTime(timezone=True)
Json = JSONB


def utcnow() -> datetime:
    return datetime.now(UTC)
