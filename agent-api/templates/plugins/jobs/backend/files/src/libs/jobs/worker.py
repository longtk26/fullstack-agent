import datetime as dt
import os
import socket
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass

from croniter import croniter
from sqlalchemy import Engine, or_
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, col, select

from src.configs import get_logger

from .models import JobModel, JobScheduleModel, utc_now
from .queue import JobQueue
from .registry import JOBS, JobContext, load_jobs

logger = get_logger(__name__)
LEASE = dt.timedelta(minutes=10)  # a running job whose worker died is taken again after this


def backoff(attempt: int) -> dt.timedelta:
    """30 s, 2 min, 8 min, … capped at an hour."""
    return dt.timedelta(seconds=min(30 * 4 ** (attempt - 1), 3600))


@dataclass
class RunSummary:
    ran: int = 0
    failed: int = 0
    dead: int = 0


class Worker:
    """Takes due jobs with `FOR UPDATE SKIP LOCKED` (two workers never take the same job), runs each in a session of
    its own, retries with `backoff`, and marks a job dead after its last attempt. Cron jobs are enqueued once per tick
    by whichever worker takes the schedule row."""

    def __init__(
        self,
        engine: Engine,
        worker_id: str | None = None,
        batch: int = 10,
        retry_after: Callable[[int], dt.timedelta] = backoff,
    ):
        load_jobs()
        self.engine = engine
        self.worker_id = worker_id or f"{socket.gethostname()}:{os.getpid()}"
        self.batch = batch
        self.retry_after = retry_after

    def tick_schedules(self, now: dt.datetime | None = None) -> int:
        """Enqueues the cron jobs that are due; returns how many."""
        now = now or utc_now()
        enqueued = 0
        with Session(self.engine) as session:
            for kind in JOBS.values():  # a schedule row per cron job; two workers may race to add it
                if kind.cron:
                    first = croniter(kind.cron, now).get_next(dt.datetime)
                    row = {"name": kind.name, "cron": kind.cron, "next_run_at": first}
                    session.connection().execute(insert(JobScheduleModel).values(**row).on_conflict_do_nothing())
            session.commit()
            due = select(JobScheduleModel).where(col(JobScheduleModel.next_run_at) <= now)
            for schedule in session.exec(due.with_for_update(skip_locked=True)):
                slot = schedule.next_run_at.isoformat()
                queue = JobQueue(session)
                if queue.enqueue(schedule.name, {"scheduledFor": slot}, dedupe_key=f"cron:{schedule.name}:{slot}"):
                    enqueued += 1
                schedule.next_run_at = croniter(schedule.cron, now).get_next(dt.datetime)
                session.add(schedule)
            session.commit()
        return enqueued

    def claim(self, limit: int | None = None) -> list[JobModel]:
        """Due jobs (and running ones past their lease), marked running by this worker, committed."""
        now = utc_now()
        with Session(self.engine) as session:
            query = (
                select(JobModel)
                .where(
                    or_(
                        (col(JobModel.status) == "queued") & (col(JobModel.run_at) <= now),
                        (col(JobModel.status) == "running") & (col(JobModel.locked_at) < now - LEASE),
                    )
                )
                .order_by(col(JobModel.run_at))
                .limit(limit or self.batch)
                .with_for_update(skip_locked=True)
            )
            jobs = list(session.exec(query))
            for job in jobs:
                job.status, job.locked_by, job.locked_at = "running", self.worker_id, now
                job.attempts += 1
                session.add(job)
            session.commit()
            for job in jobs:
                session.refresh(job)
                session.expunge(job)
            return jobs

    def run(self, job: JobModel) -> bool:
        """Runs one claimed job; True when it is done."""
        kind = JOBS.get(job.kind)
        error = None
        try:
            if kind is None:
                raise LookupError(f"no handler for job kind '{job.kind}'")
            with Session(self.engine) as session:
                kind.handler(dict(job.payload), JobContext(job.id, job.attempts, session))
                session.commit()
        except Exception:  # noqa: BLE001 - a handler's failure is recorded on the job, the worker goes on
            error = traceback.format_exc(limit=5)
        with Session(self.engine) as session:
            current = session.get(JobModel, job.id)
            if current is None:
                return error is None
            if error is None:
                current.status, current.finished_at, current.last_error = "done", utc_now(), None
            elif current.attempts >= current.max_attempts:
                current.status, current.finished_at, current.last_error = "dead", utc_now(), error
            else:
                current.status, current.last_error = "queued", error
                current.run_at = utc_now() + self.retry_after(current.attempts)
            current.locked_by = current.locked_at = None
            session.add(current)
            session.commit()
            if error is not None:
                logger.warning("job failed", extra={"job_id": str(job.id), "kind": job.kind, "status": current.status})
        return error is None

    def run_due(self) -> RunSummary:
        """Ticks the schedules, then runs jobs until none is due (what `--once` does)."""
        summary = RunSummary()
        self.tick_schedules()
        while jobs := self.claim():
            for job in jobs:
                summary.ran += 1
                if not self.run(job):
                    summary.failed += 1
                    summary.dead += int(job.attempts >= job.max_attempts)
        return summary

    def run_forever(self, poll_seconds: float = 1.0, stop: Callable[[], bool] = lambda: False) -> None:
        while not stop():
            if self.run_due().ran == 0:
                time.sleep(poll_seconds)
