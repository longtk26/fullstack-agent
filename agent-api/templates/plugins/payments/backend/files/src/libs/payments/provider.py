import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from src.configs import config

from .models import PaymentModel

OUTCOMES = {"checkout.completed": "paid", "checkout.failed": "failed", "checkout.canceled": "canceled"}


@dataclass(frozen=True)
class CheckoutSession:
    session_id: str
    url: str


@dataclass(frozen=True)
class PaymentEvent:
    event_id: str
    session_id: str
    outcome: str  # paid | failed | canceled


class IPaymentProvider(ABC):
    """Where a checkout happens (Story 10.9). The fake provider's page is served by this app; a real one is a
    developer's adapter. Adding Stripe: `PAYMENT_PROVIDER=stripe`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`;
    `create_checkout` creates a Checkout Session (`stripe.checkout.Session.create(mode="payment", line_items=[...],
    client_reference_id=str(payment.id), success_url=..., cancel_url=...)`) and returns its id and URL; Stripe posts
    `checkout.session.completed` to a webhook route that verifies `Stripe-Signature` (`stripe.Webhook.construct_event`)
    and enqueues the same job; `parse_webhook` maps it to a `PaymentEvent`."""

    name: str

    @abstractmethod
    def create_checkout(self, payment: PaymentModel, base_url: str) -> CheckoutSession:
        pass

    @abstractmethod
    def parse_webhook(self, event: dict[str, Any]) -> PaymentEvent | None:
        """The verified event (its signature was checked on the way in) as a payment outcome; None: not ours."""


class FakePaymentProvider(IPaymentProvider):
    """Test double (`PAYMENT_PROVIDER=fake`): a checkout page in this app pays, fails or cancels, and sends its
    outcome as a signed webhook through the real incoming path. It does not run when `APP_ENV=production`."""

    name = "fake"

    def create_checkout(self, payment: PaymentModel, base_url: str) -> CheckoutSession:
        session_id = f"fake_{secrets.token_hex(12)}"
        return CheckoutSession(session_id, f"{base_url.rstrip('/')}/payments/fake/checkout/{session_id}")

    def parse_webhook(self, event: dict[str, Any]) -> PaymentEvent | None:
        outcome = OUTCOMES.get(str(event.get("type")))
        session_id = (event.get("data") or {}).get("sessionId")
        if outcome is None or not session_id:
            return None
        return PaymentEvent(str(event.get("id")), str(session_id), outcome)


@lru_cache
def get_provider() -> IPaymentProvider:
    if config.payment_provider == "fake":
        return FakePaymentProvider()
    raise RuntimeError(f"no adapter for PAYMENT_PROVIDER={config.payment_provider!r} (see IPaymentProvider)")
