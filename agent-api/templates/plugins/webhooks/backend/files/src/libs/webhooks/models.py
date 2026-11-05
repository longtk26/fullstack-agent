import datetime as dt
import uuid
from typing import Any

from sqlalchemy import DateTime, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class WebhookSubscriptionModel(SQLModel, table=True):
    __tablename__ = "webhook_subscriptions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    url: str = Field(max_length=2048)
    secret: str = Field(max_length=128)
    events: list[str] = Field(default_factory=list, sa_type=JSONB)
    active: bool = True
    created_at: dt.datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))


class WebhookDeliveryModel(SQLModel, table=True):
    """One event to one subscription; `status`: pending → delivered, or failed after the last attempt."""

    __tablename__ = "webhook_deliveries"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    subscription_id: uuid.UUID = Field(foreign_key="webhook_subscriptions.id", ondelete="CASCADE", index=True)
    event: str = Field(max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict, sa_type=JSONB)
    status: str = Field(default="pending", max_length=16)
    attempts: int = 0
    response_code: int | None = None
    last_error: str | None = Field(default=None, sa_type=Text)
    created_at: dt.datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
    delivered_at: dt.datetime | None = Field(default=None, sa_type=DateTime(timezone=True))


class WebhookEventReceivedModel(SQLModel, table=True):
    """An incoming event's id per source: a repeat is answered 200 and ignored."""

    __tablename__ = "webhook_events_received"
    __table_args__ = (UniqueConstraint("source", "event_id", name="uq_webhook_events_received_source_event"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    source: str = Field(max_length=63)
    event_id: str = Field(max_length=255)
    event_type: str = Field(max_length=120)
    received_at: dt.datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
