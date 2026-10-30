import asyncio
import time
from collections.abc import Sequence

from redis.asyncio import Redis

JOBS_PREFIX = "bga:jobs:"  # one queue per engine, so a worker only takes jobs for engines it can run
PROCESSING_PREFIX = "bga:processing:"
LEASE_PREFIX = "bga:lease:"
CANCEL_PREFIX = "bga:cancel:"
EVENTS_PREFIX = "bga:events:"
DRAFTS_PREFIX = "bga:drafts:"  # drafting jobs (Stories 2.4, 12.4), one queue per engine like generations


def events_channel(generation_id: str) -> str:
    return f"{EVENTS_PREFIX}{generation_id}"


def jobs_key(engine: str) -> str:
    return f"{JOBS_PREFIX}{engine}"


def drafts_key(engine: str) -> str:
    return f"{DRAFTS_PREFIX}{engine}"


class JobQueue:
    """Reliable Redis queue: a job moves atomically into the worker's processing list when taken,
    so a crash leaves it visible there (and in the DB as an active job) instead of losing it."""

    def __init__(self, redis: Redis):
        self.redis = redis

    async def enqueue(self, generation_id: str, engine: str) -> None:
        await self.redis.lpush(jobs_key(engine), generation_id)

    async def dequeue(self, worker_id: str, engines: Sequence[str], timeout_s: float) -> str | None:
        """Oldest job of any of `engines`. One engine blocks on its queue; several are polled in turn."""
        processing = PROCESSING_PREFIX + worker_id
        keys = [jobs_key(engine) for engine in engines]
        if len(keys) == 1:
            return await self.redis.blmove(keys[0], processing, timeout_s, "RIGHT", "LEFT")
        deadline = time.monotonic() + timeout_s
        while True:
            for key in keys:
                generation_id = await self.redis.lmove(key, processing, "RIGHT", "LEFT")
                if generation_id is not None:
                    return generation_id
            if time.monotonic() >= deadline:
                return None
            await asyncio.sleep(0.2)

    async def enqueue_draft(self, draft_id: str, engine: str) -> None:
        await self.redis.lpush(drafts_key(engine), draft_id)

    async def dequeue_draft(self, engines: Sequence[str]) -> str | None:
        """Oldest draft of any of `engines`, without blocking. Drafts are short and claimed in the DB
        (PENDING → RUNNING), so a lost one is failed by the reaper instead of being tracked here."""
        for engine in engines:
            draft_id = await self.redis.rpop(drafts_key(engine))
            if draft_id is not None:
                return draft_id
        return None

    async def ack(self, worker_id: str, generation_id: str) -> None:
        await self.redis.lrem(PROCESSING_PREFIX + worker_id, 0, generation_id)

    async def remove_queued(self, generation_id: str) -> int:
        removed = 0
        async for key in self.redis.scan_iter(match=JOBS_PREFIX + "*"):
            removed += await self.redis.lrem(key, 0, generation_id)
        return removed

    async def is_queued(self, generation_id: str) -> bool:
        async for key in self.redis.scan_iter(match=JOBS_PREFIX + "*"):
            if await self.redis.lpos(key, generation_id) is not None:
                return True
        return False

    async def is_processing(self, generation_id: str) -> bool:
        async for key in self.redis.scan_iter(match=PROCESSING_PREFIX + "*"):
            if await self.redis.lpos(key, generation_id) is not None:
                return True
        return False

    async def drop_from_processing(self, generation_id: str) -> None:
        async for key in self.redis.scan_iter(match=PROCESSING_PREFIX + "*"):
            await self.redis.lrem(key, 0, generation_id)

    async def claim(self, generation_id: str, worker_id: str, ttl_s: int) -> bool:
        """Atomic: only one worker can hold a job, even if it was enqueued twice."""
        return bool(await self.redis.set(LEASE_PREFIX + generation_id, worker_id, ex=ttl_s, nx=True))

    async def hold_lease(self, generation_id: str, worker_id: str, ttl_s: int) -> None:
        await self.redis.set(LEASE_PREFIX + generation_id, worker_id, ex=ttl_s)

    async def lease_owner(self, generation_id: str) -> str | None:
        return await self.redis.get(LEASE_PREFIX + generation_id)

    async def clear_processing(self, worker_id: str) -> list[str]:
        """At startup a worker owns nothing: whatever its previous incarnation left is handed to the reaper."""
        key = PROCESSING_PREFIX + worker_id
        leftovers = await self.redis.lrange(key, 0, -1)
        await self.redis.delete(key)
        return leftovers

    async def has_lease(self, generation_id: str) -> bool:
        return bool(await self.redis.exists(LEASE_PREFIX + generation_id))

    async def release_lease(self, generation_id: str) -> None:
        await self.redis.delete(LEASE_PREFIX + generation_id)

    async def request_cancel(self, generation_id: str) -> None:
        await self.redis.publish(CANCEL_PREFIX + generation_id, "cancel")
