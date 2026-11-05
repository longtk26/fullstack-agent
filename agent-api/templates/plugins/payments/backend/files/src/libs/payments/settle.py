from enum import Enum
from typing import Any

from sqlmodel import Session, col, select

from src.configs import get_logger
from src.libs.jobs import JobQueue

from .catalog import PAYABLE
from .models import PaymentModel, utc_now
from .provider import get_provider

logger = get_logger(__name__)


def _state(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


def settle(session: Session, event: dict[str, Any]) -> None:
    """A provider's verified event (a job): the payment's outcome, and the record's status with it. Idempotent: a
    payment that is no longer pending is left as it is."""
    parsed = get_provider().parse_webhook(event)
    if parsed is None:
        return
    payment = session.exec(select(PaymentModel).where(col(PaymentModel.session_id) == parsed.session_id)).first()
    if payment is None or payment.status != "pending":
        return
    payment.status, payment.raw_event, payment.updated_at = parsed.outcome, event, utc_now()
    target = {"paid": PAYABLE.paid, "failed": PAYABLE.failed}.get(parsed.outcome)
    record = session.get(PAYABLE.model, PAYABLE.record_key(payment.record_id))
    current = getattr(record, PAYABLE.status) if record is not None else None
    if record is not None and target is not None:
        try:
            if PAYABLE.transition is not None:  # the spec's transition rule decides (10.4)
                PAYABLE.transition.check(current, target)
            setattr(record, PAYABLE.status, PAYABLE.status_enum(target))
            session.add(record)
        except Exception as exc:  # noqa: BLE001 - the payment is recorded; the record keeps its state
            payment.last_error = str(exc)[:1000]
            logger.warning("record status not changed", extra={"payment_id": str(payment.id), "error": str(exc)})
    session.add(payment)
    if parsed.outcome == "paid":  # email and webhooks may subscribe
        JobQueue(session).emit(
            PAYABLE.event,
            {
                "id": payment.record_id,
                "paymentId": str(payment.id),
                "amount": str(payment.amount),
                "currency": payment.currency,
            },
        )
    logger.info(
        "payment settled",
        extra={
            "payment_id": str(payment.id),
            "outcome": parsed.outcome,
            "record": payment.record_id,
            "previous": _state(current) if record else None,
        },
    )
