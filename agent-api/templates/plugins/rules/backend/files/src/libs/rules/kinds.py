"""Predefined business rules (Story 10.4). Each check raises the error the API contract lists for it, with the field
(its API name) in `details.fields`, so a client marks it."""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from http import HTTPStatus
from typing import Any

from src.libs.exceptions import ConflictException, ErrorCode
from src.libs.exceptions.base_exception import BaseException as AppException


def _state(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


def _amount(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


@dataclass(frozen=True)
class Transition:
    """`field` moves only along `allowed` (a state → its next states); keeping the same state is always allowed."""

    rule: str
    field: str
    allowed: dict[str, tuple[str, ...]]

    def next_states(self, current: Any) -> tuple[str, ...]:
        return self.allowed.get(_state(current), ())

    def check(self, current: Any, new: Any) -> None:
        if new is None or _state(new) == _state(current):
            return
        if _state(new) not in self.next_states(current):
            raise ConflictException(
                f"{self.field} cannot change from {_state(current)} to {_state(new)}",
                ErrorCode.INVALID_TRANSITION,
                details={
                    "fields": [self.field],
                    "rule": self.rule,
                    "from": _state(current),
                    "to": _state(new),
                    "allowed": list(self.next_states(current)),
                },
            )


@dataclass(frozen=True)
class ImmutableAfter:
    """A record whose `field` is in `states` cannot be changed or deleted."""

    rule: str
    field: str
    states: tuple[str, ...]

    def locked(self, value: Any) -> bool:
        return _state(value) in self.states

    def check(self, value: Any) -> None:
        if self.locked(value):
            raise ConflictException(
                f"The record cannot change once {self.field} is {_state(value)}",
                ErrorCode.RESOURCE_LOCKED,
                details={"fields": [self.field], "rule": self.rule, "state": _state(value)},
            )


@dataclass(frozen=True)
class SumEquals:
    """`field`, when sent, equals the total of the record's items (to the cent)."""

    rule: str
    field: str

    def check(self, value: Any, total: Any) -> None:
        if value is None or _amount(value) == _amount(total):
            return
        raise AppException(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            f"{self.field} must equal the items' total, {_amount(total)}",
            ErrorCode.TOTAL_MISMATCH,
            details={"fields": [self.field], "rule": self.rule, "expected": str(_amount(total))},
        )
