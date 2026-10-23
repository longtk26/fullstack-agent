import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlmodel import Session

from src.configs import config
from src.engines import EngineRegistry
from src.engines.fake_engine import FakeEngine, FakeStep
from src.libs.database import db_session_manager
from src.libs.queue import JobQueue
from src.libs.redaction import Redactor
from src.modules.generations.infrastructure.adapters import EventPublisher
from src.modules.shared.infrastructure.models import GenerationModel
from src.orchestrator.store import JobStore
from src.orchestrator.worker_service import WorkerService
from src.orchestrator.workspace import WorkspaceManager
from workflow_helpers import build_runner, events, generation, redis_client, submit

pytestmark = pytest.mark.usefixtures("clean_redis")


def _service(root: Path, redis, engine=None, worker_id="w-test") -> WorkerService:
    engine = engine or FakeEngine(allowed_root=root)
    runner = build_runner(root, redis, engine=engine, worker_id=worker_id)
    return WorkerService(
        runner,
        JobQueue(redis),
        JobStore(),
        EventPublisher(redis, Redactor()),
        redis,
        EngineRegistry([engine], default=engine.name),
        WorkspaceManager(root, max_mb=200),
        worker_id,
        concurrency=2,
    )


def _force(generation_id: str, **fields) -> None:
    with Session(db_session_manager.engine) as session:
        row = session.get(GenerationModel, generation_id)
        for key, value in fields.items():
            setattr(row, key, value)
        session.add(row)
        session.commit()


async def _wait_for_status(generation_id: str, wanted: set[str], timeout_s: float = 30) -> str:
    for _ in range(int(timeout_s * 10)):
        status = generation(generation_id).status
        if status in wanted:
            return status
        await asyncio.sleep(0.1)
    raise AssertionError(f"{generation_id} stuck in {generation(generation_id).status}")


def test_worker_consumes_the_queue_end_to_end(client, user_headers, tmp_path):
    ids = [submit(client, user_headers) for _ in range(2)]

    async def scenario():
        redis = redis_client()
        stop = asyncio.Event()
        service = _service(tmp_path, redis)
        task = asyncio.create_task(service.run(stop))
        try:
            return [await _wait_for_status(i, {"COMPLETED", "FAILED"}) for i in ids]
        finally:
            stop.set()
            await asyncio.wait_for(task, timeout=15)
            leases = [await redis.exists(f"bga:lease:{i}") for i in ids]
            processing = await redis.llen("bga:processing:w-test")
            await redis.aclose()
            assert leases == [0, 0] and processing == 0, "jobs are acked and leases released"

    assert asyncio.run(scenario()) == ["COMPLETED", "COMPLETED"]
    assert generation(ids[0]).worker_id == "w-test"


def test_cancel_through_the_api_reaches_the_worker(client, user_headers, tmp_path):
    engine = FakeEngine(tmp_path, {"*": [FakeStep(sleep_s=60)]})
    generation_id = submit(client, user_headers)

    async def scenario():
        redis = redis_client()
        stop = asyncio.Event()
        task = asyncio.create_task(_service(tmp_path, redis, engine=engine).run(stop))
        try:
            await _wait_for_status(generation_id, {"RUNNING"})
            await asyncio.sleep(0.5)
            response = await asyncio.to_thread(
                client.post, f"/api/v1/generations/{generation_id}/cancel", headers=user_headers
            )
            assert response.status_code == 202
            return await _wait_for_status(generation_id, {"CANCELLED", "FAILED", "COMPLETED"}, timeout_s=10)
        finally:
            stop.set()
            await asyncio.wait_for(task, timeout=15)
            await redis.aclose()

    assert asyncio.run(scenario()) == "CANCELLED"


def test_reaper_requeues_stale_jobs_and_gives_up_after_max_resumes(client, user_headers, tmp_path):
    stale = datetime.now(UTC) - timedelta(minutes=5)
    resumable = submit(client, user_headers)
    exhausted = submit(client, user_headers)
    leased = submit(client, user_headers)
    _force(resumable, status="RUNNING", heartbeat_at=stale)
    _force(exhausted, status="RUNNING", heartbeat_at=stale, resume_count=config.worker_max_resumes)
    _force(leased, status="RUNNING", heartbeat_at=stale)

    async def scenario():
        redis = redis_client()
        try:
            queue = JobQueue(redis)
            await redis.delete("bga:jobs")
            await queue.hold_lease(leased, "other-worker", 30)
            await _service(tmp_path, redis).reap()
            return await redis.lrange("bga:jobs", 0, -1)
        finally:
            await redis.aclose()

    queued = asyncio.run(scenario())

    assert queued == [resumable]
    assert generation(resumable).resume_count == 1
    assert generation(exhausted).status == "FAILED"
    assert events(exhausted)[-1].payload["errorCode"] == "WORKER_LOST"
    assert generation(leased).status == "RUNNING", "a job with a live lease belongs to another worker"


def test_reaper_reenqueues_orphaned_pending_jobs(client, user_headers, tmp_path):
    generation_id = submit(client, user_headers)
    _force(generation_id, created_at=datetime.now(UTC) - timedelta(minutes=2))

    async def scenario():
        redis = redis_client()
        try:
            await redis.delete("bga:jobs")  # the enqueue after commit was lost
            await _service(tmp_path, redis).reap()
            return await redis.lrange("bga:jobs", 0, -1)
        finally:
            await redis.aclose()

    assert generation_id in asyncio.run(scenario())


def test_old_finished_workspaces_are_deleted(client, user_headers, tmp_path):
    old, recent = submit(client, user_headers), submit(client, user_headers)
    _force(
        old, status="COMPLETED", finished_at=datetime.now(UTC) - timedelta(hours=config.workspace_retention_hours + 1)
    )
    _force(recent, status="COMPLETED", finished_at=datetime.now(UTC))
    for generation_id in (old, recent):
        (tmp_path / generation_id).mkdir()

    async def scenario():
        redis = redis_client()
        try:
            _service(tmp_path, redis).cleanup_workspaces()
        finally:
            await redis.aclose()

    asyncio.run(scenario())

    assert not (tmp_path / old).exists() and (tmp_path / recent).exists()


def test_consume_loop_survives_redis_outages(tmp_path):
    from redis.exceptions import ConnectionError as RedisConnectionError

    class FlakyQueue(JobQueue):
        def __init__(self, redis):
            super().__init__(redis)
            self.calls = 0

        async def dequeue(self, worker_id, timeout_s):
            self.calls += 1
            if self.calls <= 2:
                raise RedisConnectionError("Connection closed by server.")
            await asyncio.sleep(0.05)
            return None

    async def scenario():
        redis = redis_client()
        try:
            service = _service(tmp_path, redis)
            service.queue = FlakyQueue(redis)
            stop = asyncio.Event()
            consumer = asyncio.create_task(service._consume(stop))
            for _ in range(100):
                await asyncio.sleep(0.1)
                if service.queue.calls >= 4:
                    break
            stop.set()
            await asyncio.wait_for(consumer, timeout=5)
            return service.queue.calls
        finally:
            await redis.aclose()

    assert asyncio.run(scenario()) >= 4, "the loop kept polling after two connection errors"


def test_cancel_flag_in_the_database_is_honoured_between_nodes(client, user_headers, tmp_path):
    from workflow_helpers import run_job

    generation_id = submit(client, user_headers)
    _force(generation_id, cancel_requested=True, status="RUNNING")

    assert run_job(tmp_path, generation_id) == "CANCELLED"


def test_pending_job_stuck_in_a_dead_workers_processing_list_is_recovered(client, user_headers, tmp_path):
    generation_id = submit(client, user_headers)
    _force(generation_id, created_at=datetime.now(UTC) - timedelta(minutes=2))

    async def scenario():
        redis = redis_client()
        try:
            await redis.delete("bga:jobs")
            await redis.lpush("bga:processing:dead-worker", generation_id)  # taken, then the worker died
            await _service(tmp_path, redis).reap()
            return await redis.lrange("bga:jobs", 0, -1), await redis.llen("bga:processing:dead-worker")
        finally:
            await redis.aclose()

    queued, left_in_dead_list = asyncio.run(scenario())

    assert generation_id in queued
    assert left_in_dead_list == 0


def test_a_restarted_worker_clears_its_own_processing_list(client, user_headers, tmp_path):
    generation_id = submit(client, user_headers)

    async def scenario():
        redis = redis_client()
        try:
            await redis.lpush("bga:processing:w-test", generation_id)
            stop = asyncio.Event()
            stop.set()  # start, do the startup housekeeping, stop
            await _service(tmp_path, redis).run(stop)
            return await redis.llen("bga:processing:w-test")
        finally:
            await redis.aclose()

    assert asyncio.run(scenario()) == 0


def test_a_job_enqueued_twice_runs_once(client, user_headers, tmp_path):
    generation_id = submit(client, user_headers)

    async def scenario():
        redis = redis_client()
        try:
            queue = JobQueue(redis)
            assert await queue.claim(generation_id, "worker-a", 30)
            service = _service(tmp_path, redis, worker_id="worker-b")
            await service._run_job(generation_id)
            return generation(generation_id).status
        finally:
            await redis.aclose()

    assert asyncio.run(scenario()) == "PENDING", "worker-b saw worker-a's lease and did not run the job"
