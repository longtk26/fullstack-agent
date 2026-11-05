import importlib
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlmodel import Session


@dataclass(frozen=True)
class JobContext:
    """What a handler gets besides the payload: the job's id (handlers are idempotent by it), the attempt (from 1),
    and a session of its own, committed when the handler returns."""

    job_id: uuid.UUID
    attempt: int
    session: Session


Handler = Callable[[dict[str, Any], JobContext], None]


@dataclass(frozen=True)
class JobKind:
    name: str
    handler: Handler
    events: tuple[str, ...] = ()
    cron: str | None = None
    max_attempts: int = 5


JOBS: dict[str, JobKind] = {}


def job(name: str, *, events: tuple[str, ...] = (), cron: str | None = None, max_attempts: int = 5):
    """Registers a handler: `@job("sendReminder", events=("booking.created",))`."""

    def register(handler: Handler) -> Handler:
        JOBS[name] = JobKind(name, handler, tuple(events), cron, max_attempts)
        return handler

    return register


def load_jobs() -> None:
    """Imports the app's job handlers (`src/jobs`), once: the API emits events, the worker runs them."""
    importlib.import_module("src.jobs")


def subscribers(event: str) -> list[JobKind]:
    load_jobs()
    return [kind for kind in JOBS.values() if event in kind.events]
