import datetime as dt
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class PaymentModel(SQLModel, table=True):
    """One checkout of one record (Story 10.9). `status`: pending → paid, failed or canceled, as the provider says."""

    __tablename__ = "payments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    entity: str = Field(max_length=63)
    record_id: str = Field(max_length=64, index=True)
    provider: str = Field(max_length=32)
    session_id: str = Field(max_length=255, unique=True)
    status: str = Field(default="pending", max_length=16)
    amount: Decimal = Field(sa_type=Numeric(18, 4))
    currency: str = Field(max_length=3)
    success_url: str | None = Field(default=None, max_length=2048)
    cancel_url: str | None = Field(default=None, max_length=2048)
    raw_event: dict[str, Any] | None = Field(default=None, sa_type=JSONB)
    last_error: str | None = Field(default=None, sa_type=Text)
    created_at: dt.datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
    updated_at: dt.datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
