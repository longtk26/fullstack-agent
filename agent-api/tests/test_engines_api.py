import asyncio

import pytest

from src.engines import EngineHealth, EngineHealthStore
from src.engines.health_store import HEALTH_KEY
from src.libs.redis import get_redis


def _headers(login):
    return {"Authorization": f"Bearer {login('user@test.local', 'userpass')}"}


async def _redis_call(fn):
    # A fresh client per event loop: the cached app client is bound to the TestClient's loop.
    from redis.asyncio import Redis

    from src.configs import config

    client = Redis.from_url(config.redis_url, decode_responses=True)
    try:
        return await fn(client)
    finally:
        await client.aclose()


@pytest.fixture(autouse=True)
def clear_health():
    asyncio.run(_redis_call(lambda r: r.delete(HEALTH_KEY)))
    yield
    asyncio.run(_redis_call(lambda r: r.delete(HEALTH_KEY)))


def test_reports_worker_published_health(client, login):
    report = [EngineHealth(name="claude_code", available=True), EngineHealth(name="fake", available=True)]
    asyncio.run(_redis_call(lambda r: EngineHealthStore(r).publish(report)))

    body = client.get("/api/v1/engines", headers=_headers(login)).json()

    assert body["reportedByWorker"] is True
    assert {e["name"]: e["available"] for e in body["engines"]} == {"claude_code": True, "fake": True}
    assert body["default"] == "claude_code"


def test_without_a_worker_report_real_engines_are_unavailable(client, login):
    body = client.get("/api/v1/engines", headers=_headers(login)).json()

    engines = {e["name"]: e for e in body["engines"]}
    assert body["reportedByWorker"] is False
    assert engines["fake"]["available"] is True
    assert engines["claude_code"]["available"] is False
    assert engines["claude_code"]["reason"].startswith("Worker not reporting")


def test_engines_require_auth(client):
    assert client.get("/api/v1/engines").status_code == 401


def test_redis_client_is_shared():
    assert get_redis() is get_redis()
