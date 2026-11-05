import datetime as dt
import uuid
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session

from src.libs.database.session import SessionDep

from .models import JobModel, utc_now
from .registry import JOBS, subscribers


class JobQueue:
    """Enqueues in the caller's transaction (the request's session): a job enqueued by a request that rolls back
    never exists, so it never runs."""

    def __init__(self, session: SessionDep):
        self.session: Session = session

    def enqueue(
        self,
        kind: str,
        payload: dict[str, Any] | None = None,
        *,
        run_at: dt.datetime | None = None,
        dedupe_key: str | None = None,
    ) -> uuid.UUID | None:
        """The new job's id; None when a job with the same `dedupe_key` exists already."""
        known = JOBS.get(kind)
        values = {
            "id": uuid.uuid4(),
            "kind": kind,
            "payload": payload or {},
            "status": "queued",
            "attempts": 0,
            "max_attempts": known.max_attempts if known else 5,
            "run_at": run_at or utc_now(),
            "dedupe_key": dedupe_key,
            "created_at": utc_now(),
        }
        statement = insert(JobModel).values(**values).on_conflict_do_nothing(index_elements=["dedupe_key"])
        row = self.session.connection().execute(statement.returning(JobModel.id)).first()  # same transaction
        return row[0] if row else None

    def emit(self, event: str, payload: dict[str, Any]) -> list[uuid.UUID]:
        """An event (`task.created`, an operation id): one job per job that subscribes to it."""
        ids = [self.enqueue(kind.name, {"event": event, **payload}) for kind in subscribers(event)]
        return [job_id for job_id in ids if job_id is not None]


JobQueueDep = Annotated[JobQueue, Depends(JobQueue)]
