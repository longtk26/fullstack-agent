from redis.asyncio import Redis

JOBS_KEY = "bga:jobs"
PROCESSING_PREFIX = "bga:processing:"
LEASE_PREFIX = "bga:lease:"
CANCEL_PREFIX = "bga:cancel:"
EVENTS_PREFIX = "bga:events:"


def events_channel(generation_id: str) -> str:
    return f"{EVENTS_PREFIX}{generation_id}"


class JobQueue:
    """Reliable Redis queue: a job moves atomically into the worker's processing list when taken,
    so a crash leaves it visible there (and in the DB as an active job) instead of losing it."""

    def __init__(self, redis: Redis):
        self.redis = redis

    async def enqueue(self, generation_id: str) -> None:
        await self.redis.lpush(JOBS_KEY, generation_id)

    async def dequeue(self, worker_id: str, timeout_s: float) -> str | None:
        return await self.redis.blmove(JOBS_KEY, PROCESSING_PREFIX + worker_id, timeout_s, "RIGHT", "LEFT")

    async def ack(self, worker_id: str, generation_id: str) -> None:
        await self.redis.lrem(PROCESSING_PREFIX + worker_id, 0, generation_id)

    async def remove_queued(self, generation_id: str) -> int:
        return await self.redis.lrem(JOBS_KEY, 0, generation_id)

    async def is_queued(self, generation_id: str) -> bool:
        return await self.redis.lpos(JOBS_KEY, generation_id) is not None

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
