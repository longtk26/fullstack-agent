from datetime import UTC, datetime

from pydantic import BaseModel
from redis.asyncio import Redis

from .port import EngineHealth

HEALTH_PREFIX = "bga:engines:health:"


class EngineHealthReport(BaseModel):
    reported_at: datetime
    engines: list[EngineHealth]


class _EngineReport(BaseModel):
    reported_at: datetime
    health: EngineHealth


class EngineHealthStore:
    """Workers own the engine CLIs, so they report their health; the API only reads the reports.

    One key per engine: each worker reports only the engines it runs (e.g. the Docker worker for Claude Code, a
    host worker for Antigravity), so two workers never overwrite each other's view."""

    def __init__(self, redis: Redis, ttl_s: int = 90):
        self.redis = redis
        self.ttl_s = ttl_s

    async def publish(self, engines: list[EngineHealth]) -> None:
        now = datetime.now(UTC)
        for health in engines:
            report = _EngineReport(reported_at=now, health=health)
            await self.redis.set(HEALTH_PREFIX + health.name, report.model_dump_json(), ex=self.ttl_s)

    async def read(self, names: list[str]) -> EngineHealthReport | None:
        """Reports for `names` in that order; an engine no worker reports is unavailable. None if nobody reports."""
        raws = await self.redis.mget([HEALTH_PREFIX + name for name in names]) if names else []
        reports = {name: _EngineReport.model_validate_json(raw) for name, raw in zip(names, raws, strict=True) if raw}
        if not reports:
            return None
        engines = [
            reports[name].health
            if name in reports
            else EngineHealth(name=name, available=False, reason="No running worker serves this engine")
            for name in names
        ]
        return EngineHealthReport(reported_at=max(r.reported_at for r in reports.values()), engines=engines)
