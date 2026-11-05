import json
import uuid
from typing import Any

import httpx
from sqlmodel import Session, col, select

from src.configs import config
from src.libs.jobs import JobQueue

from .guard import check_target
from .models import WebhookDeliveryModel, WebhookSubscriptionModel, utc_now
from .signing import HEADER, sign

DELIVER = "webhooks.deliver"
MAX_ATTEMPTS = 6


def fan_out(session: Session, event: str, payload: dict[str, Any]) -> int:
    """A delivery (and its job) per active subscription to `event`, in the caller's transaction."""
    subscriptions = session.exec(select(WebhookSubscriptionModel).where(col(WebhookSubscriptionModel.active)))
    queue = JobQueue(session)
    count = 0
    for subscription in subscriptions:
        if event not in subscription.events and event != "ping":
            continue
        delivery = WebhookDeliveryModel(subscription_id=subscription.id, event=event, payload=payload)
        session.add(delivery)
        session.flush()
        queue.enqueue(DELIVER, {"deliveryId": str(delivery.id)}, dedupe_key=f"webhook-delivery:{delivery.id}")
        count += 1
    return count


def deliver(session: Session, delivery_id: uuid.UUID, attempt: int) -> None:
    """POSTs a delivery, signed, without following redirects; raises (so the job retries) unless it was accepted."""
    delivery = session.get(WebhookDeliveryModel, delivery_id)
    if delivery is None or delivery.status == "delivered":
        return  # idempotent: a retry of a delivered webhook does nothing
    subscription = session.get(WebhookSubscriptionModel, delivery.subscription_id)
    if subscription is None:
        return
    body = json.dumps(
        {"id": str(delivery.id), "type": delivery.event, "data": delivery.payload}, separators=(",", ":")
    ).encode()
    headers = {
        "Content-Type": "application/json",
        HEADER: sign(subscription.secret, body),
        "X-Webhook-Id": str(delivery.id),
        "X-Webhook-Event": delivery.event,
    }
    delivery.attempts = attempt
    try:
        check_target(subscription.url, config.webhook_allow_private)
        response = httpx.post(
            subscription.url,
            content=body,
            headers=headers,
            timeout=config.webhook_timeout_seconds,
            follow_redirects=False,
        )
        delivery.response_code = response.status_code
        if not 200 <= response.status_code < 300:
            raise RuntimeError(f"answered {response.status_code}")
    except Exception as exc:
        delivery.last_error = str(exc)[:1000]
        delivery.status = "failed" if attempt >= MAX_ATTEMPTS else "pending"
        session.add(delivery)
        session.commit()  # the attempt is recorded even though the job fails
        raise
    delivery.status, delivery.delivered_at, delivery.last_error = "delivered", utc_now(), None
    session.add(delivery)
