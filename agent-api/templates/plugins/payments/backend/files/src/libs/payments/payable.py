import uuid
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Payable:
    """What is paid for (Story 10.9, from the plan): the record's model, its status field and the paid / failed
    states, where the amount and currency come from, the event a payment raises and the rule a status change obeys."""

    entity: str
    model: type
    status: str
    status_enum: type
    paid: str
    failed: str | None
    amount: str
    currency: str | None
    currency_field: str | None
    event: str
    transition: Any = None
    key_type: str = "uuid"

    def record_key(self, value: str) -> Any:
        if self.key_type == "uuid":
            return uuid.UUID(value)
        return int(value) if self.key_type == "integer" else value
