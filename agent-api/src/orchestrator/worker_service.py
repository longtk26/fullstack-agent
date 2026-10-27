import asyncio
import socket
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.configs import config, get_logger
from src.engines import EngineHealthStore, EngineRegistry
from src.libs.queue import CANCEL_PREFIX, JobQueue
from src.modules.generations.infrastructure.adapters import EventPublisher
from src.modules.shared.domain.enums import GenerationStatus
from src.modules.shared.domain.generation_modes import close_lanes

from .previews import PreviewService
from .runner import JobRunner
from .store import JobStore
from .workspace import WorkspaceManager

logger = get_logger(__name__)
ENGINE_HEALTH_INTERVAL_S = 30
PENDING_GRACE_S = 30
MAX_BACKOFF_S = 10.0
# Redis or Postgres restarting must not take the worker down; these are retried with backoff.
TRANSIENT_ERRORS = (RedisError, ConnectionError, OSError)


def default_worker_id() -> str:
    import os

    return f"{socket.gethostname()}-{os.getpid()}"


class WorkerService:
    def __init__(
        self,
        runner: JobRunner,
        queue: JobQueue,
        store: JobStore,
        events: EventPublisher,
        redis: Redis,
        registry: EngineRegistry,
        workspaces: WorkspaceManager,
        worker_id: str,
        concurrency: int = config.worker_concurrency,
        previews: PreviewService | None = None,
        engines: list[str] | None = None,
    ):
        self.runner = runner
        self.queue = queue
        self.store = store
        self.events = events
        self.redis = redis
        self.registry = registry
        wanted = engines or config.worker_engine_list
        self.engines = [name for name in registry.names() if not wanted or name in wanted]
        self.workspaces = workspaces
        self.worker_id = worker_id
        self.concurrency = concurrency
        self.previews = previews
        self.tasks: dict[str, asyncio.Task] = {}
        self.preview_tasks: set[asyncio.Task] = set()
        self._shutting_down = False

    async def run(self, stop: asyncio.Event) -> None:
        logger.info(
            "worker started",
            extra={"worker_id": self.worker_id, "concurrency": self.concurrency, "engines": self.engines},
        )
        leftovers = await self.queue.clear_processing(self.worker_id)
        if leftovers:
            logger.warning("found jobs from a previous run of this worker", extra={"generation_ids": leftovers})
        await self.reap()
        background = [
            asyncio.create_task(self._cancel_listener()),
            asyncio.create_task(self._periodic(stop)),
        ]
        if self.previews is not None:
            background.append(asyncio.create_task(self._preview_commands(stop)))
        try:
            await self._consume(stop)
        finally:
            await self._shutdown()
            for task in background:
                task.cancel()
            await asyncio.gather(*background, return_exceptions=True)
        logger.info("worker stopped", extra={"worker_id": self.worker_id})

    async def _consume(self, stop: asyncio.Event) -> None:
        slots = asyncio.Semaphore(self.concurrency)
        backoff = 0.5
        while not stop.is_set():
            await slots.acquire()
            if stop.is_set():
                slots.release()
                break
            try:
                generation_id = await self.queue.dequeue(self.worker_id, self.engines, timeout_s=1)
            except TRANSIENT_ERRORS as exc:
                slots.release()
                logger.warning("queue unavailable, retrying", extra={"error": str(exc), "retry_in_s": backoff})
                await _sleep_or_stop(stop, backoff)
                backoff = min(backoff * 2, MAX_BACKOFF_S)
                continue
            backoff = 0.5
            if generation_id is None:
                slots.release()
                continue
            task = asyncio.create_task(self._run_job(generation_id))
            self.tasks[generation_id] = task

            def done(_: asyncio.Task, gen=generation_id) -> None:
                self.tasks.pop(gen, None)
                slots.release()

            task.add_done_callback(done)

    async def _run_job(self, generation_id: str) -> None:
        if not await self.queue.claim(generation_id, self.worker_id, config.worker_lease_ttl_seconds):
            if await self.queue.lease_owner(generation_id) != self.worker_id:
                logger.warning("job already claimed by another worker", extra={"generation_id": generation_id})
                await self.queue.ack(self.worker_id, generation_id)
                return
        heartbeat = asyncio.create_task(self._heartbeat(generation_id))
        try:
            await self.runner.run(generation_id)
        except asyncio.CancelledError:
            raise  # shutdown: no ack, the lease lapses and the reaper resumes the job
        except Exception:
            logger.exception("job runner failed", extra={"generation_id": generation_id})
        else:
            await self.queue.release_lease(generation_id)
        finally:
            heartbeat.cancel()
            if not self._shutting_down:
                await self.queue.ack(self.worker_id, generation_id)

    async def _heartbeat(self, generation_id: str) -> None:
        interval = max(1, config.worker_lease_ttl_seconds // 3)
        while True:
            try:
                await self.queue.hold_lease(generation_id, self.worker_id, config.worker_lease_ttl_seconds)
                self.store.update_generation(generation_id, heartbeat_at=datetime.now(UTC))
            except Exception as exc:  # keep beating; one missed beat is fine, a dead heartbeat task is not
                logger.warning("heartbeat failed", extra={"generation_id": generation_id, "error": str(exc)})
            await asyncio.sleep(interval)

    async def _cancel_listener(self) -> None:
        backoff = 0.5
        while True:
            pubsub = self.redis.pubsub()
            try:
                await pubsub.psubscribe(CANCEL_PREFIX + "*")
                backoff = 0.5
                while True:
                    # Polling with a timeout (rather than listen()) stays below the Redis socket timeout.
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=5)
                    if message is None or message.get("type") != "pmessage":
                        continue
                    channel = message["channel"]
                    generation_id = channel.decode() if isinstance(channel, bytes) else channel
                    await self.runner.cancel(generation_id.removeprefix(CANCEL_PREFIX))
            except TRANSIENT_ERRORS as exc:
                # Cancels sent while disconnected are not lost: the DB flag is checked between nodes.
                logger.warning("cancel listener reconnecting", extra={"error": str(exc)})
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, MAX_BACKOFF_S)
            finally:
                await pubsub.aclose()

    async def _preview_commands(self, stop: asyncio.Event) -> None:
        """Preview commands from the API (start, stop, logs, …); each runs as its own task."""
        backoff = 0.5
        while not stop.is_set():
            try:
                command = await self.previews.bus.next(timeout_s=1)
                backoff = 0.5
            except TRANSIENT_ERRORS as exc:
                logger.warning("preview command queue unavailable", extra={"error": str(exc)})
                await _sleep_or_stop(stop, backoff)
                backoff = min(backoff * 2, MAX_BACKOFF_S)
                continue
            if command is not None:
                task = asyncio.create_task(self.previews.handle(command))
                self.preview_tasks.add(task)
                task.add_done_callback(self.preview_tasks.discard)

    async def _periodic(self, stop: asyncio.Event) -> None:
        heartbeat_file = Path(config.worker_heartbeat_file)
        health_store = EngineHealthStore(self.redis)
        last_health = last_reap = last_reconcile = 0.0
        while not stop.is_set():
            heartbeat_file.touch()
            now = time.monotonic()
            try:
                if now - last_health >= ENGINE_HEALTH_INTERVAL_S:
                    served = [h for h in await self.registry.health() if h.name in self.engines]
                    await health_store.publish(served)
                    last_health = now
                if now - last_reap >= config.reaper_interval_seconds:
                    await self.reap()
                    self.cleanup_workspaces()
                    await self.cleanup_sandboxes()
                    if self.previews is not None:
                        await self.previews.expire()
                    last_reap = now
                if self.previews is not None and now - last_reconcile >= config.preview_reconcile_seconds:
                    await self.previews.reconcile()
                    last_reconcile = now
            except Exception:  # housekeeping must never take the worker down
                logger.exception("worker housekeeping failed")
            try:
                await asyncio.wait_for(stop.wait(), timeout=config.worker_heartbeat_seconds)
            except TimeoutError:
                pass

    async def reap(self) -> None:
        now = datetime.now(UTC)
        for generation in self.store.stale_active(now - timedelta(seconds=config.worker_lease_ttl_seconds)):
            if generation.id in self.tasks or await self.queue.has_lease(generation.id):
                continue
            await self.queue.drop_from_processing(generation.id)
            if generation.resume_count >= config.worker_max_resumes:
                message = f"Worker lost {generation.resume_count + 1} times; giving up"
                self.store.update_generation(
                    generation.id,
                    status=GenerationStatus.FAILED,
                    error_summary=message,
                    finished_at=now,
                    lanes=close_lanes(generation.lanes, failed=True),
                )
                await self.events.publish(
                    generation.id,
                    "status.changed",
                    status=GenerationStatus.FAILED,
                    payload={"errorCode": "WORKER_LOST", "errorSummary": message},
                )
                continue
            self.store.update_generation(generation.id, resume_count=generation.resume_count + 1, heartbeat_at=now)
            await self.queue.enqueue(generation.id, generation.engine)
            await self.events.publish(
                generation.id,
                "job.requeued",
                payload={"reason": "worker lost", "resumeCount": generation.resume_count + 1},
            )
            logger.warning("requeued stale generation", extra={"generation_id": generation.id})

        for generation in self.store.pending_before(now - timedelta(seconds=PENDING_GRACE_S)):
            # A claimed job always has a lease, so "no lease and not queued" means nobody will run it.
            if not await self.queue.has_lease(generation.id) and not await self.queue.is_queued(generation.id):
                await self.queue.drop_from_processing(generation.id)
                await self.queue.enqueue(generation.id, generation.engine)
                logger.warning("re-enqueued orphaned pending generation", extra={"generation_id": generation.id})

    async def cleanup_sandboxes(self) -> int:
        """Removes sandboxes whose generation finished or vanished (e.g. a worker died mid-job)."""
        provider = self.runner.sandboxes
        if provider is None:
            return 0
        orphans = set()
        for generation_id in await provider.job_ids():
            generation = self.store.generation(generation_id)
            if generation is None or generation.status.is_terminal:
                orphans.add(generation_id)
        removed = await provider.remove(orphans) if orphans else 0
        if removed:
            logger.info("removed orphaned sandboxes", extra={"generations": sorted(orphans)})
        return removed

    def cleanup_workspaces(self) -> None:
        cutoff = datetime.now(UTC) - timedelta(hours=config.workspace_retention_hours)
        expired = set(self.store.finished_before(cutoff)) & set(self.workspaces.existing_ids())
        for generation_id in expired:
            self.workspaces.delete(generation_id)
        if config.trace_retention_days:
            # Trace detail (model calls, sandbox commands) goes; node runs, invocations and report.json stay.
            old = self.store.finished_before(datetime.now(UTC) - timedelta(days=config.trace_retention_days))
            if old and self.store.prune_trace_details(old):
                logger.info("pruned trace details", extra={"generations": len(old)})

    async def _shutdown(self) -> None:
        if not self.tasks:
            return
        logger.info("waiting for running jobs", extra={"jobs": list(self.tasks)})
        _, pending = await asyncio.wait(list(self.tasks.values()), timeout=config.worker_shutdown_grace_seconds)
        if pending:
            self._shutting_down = True
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)


async def _sleep_or_stop(stop: asyncio.Event, seconds: float) -> None:
    try:
        await asyncio.wait_for(stop.wait(), timeout=seconds)
    except TimeoutError:
        pass
