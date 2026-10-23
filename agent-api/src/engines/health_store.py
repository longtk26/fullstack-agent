import json
from datetime import UTC, datetime

from pydantic import BaseModel
from redis.asyncio import Redis

from .port import EngineHealth

HEALTH_KEY = "bga:engines:health"


class EngineHealthReport(BaseModel):
    reported_at: datetime
    engines: list[EngineHealth]


class EngineHealthStore:
    """The worker owns the engine CLIs, so it reports their health; the API only reads the report."""

    def __init__(self, redis: Redis, ttl_s: int = 90):
        self.redis = redis
        self.ttl_s = ttl_s

    async def publish(self, engines: list[EngineHealth]) -> None:
        report = EngineHealthReport(reported_at=datetime.now(UTC), engines=engines)
        await self.redis.set(HEALTH_KEY, report.model_dump_json(), ex=self.ttl_s)

    async def read(self) -> EngineHealthReport | None:
        raw = await self.redis.get(HEALTH_KEY)
        return EngineHealthReport.model_validate(json.loads(raw)) if raw else None
