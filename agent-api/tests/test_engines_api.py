import asyncio

import pytest

from src.engines import EngineHealth, EngineHealthStore
from src.engines.health_store import HEALTH_PREFIX
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


async def _clear(redis):
    keys = [key async for key in redis.scan_iter(match=HEALTH_PREFIX + "*")]
    if keys:
        await redis.delete(*keys)


@pytest.fixture(autouse=True)
def clear_health():
    asyncio.run(_redis_call(_clear))
    yield
    asyncio.run(_redis_call(_clear))


def test_reports_worker_published_health(client, login):
    report = [EngineHealth(name="claude_code", available=True), EngineHealth(name="fake", available=True)]
    asyncio.run(_redis_call(lambda r: EngineHealthStore(r).publish(report)))

    body = client.get("/api/v1/engines", headers=_headers(login)).json()

    assert body["reportedByWorker"] is True
    engines = {e["name"]: e for e in body["engines"]}
    assert engines["claude_code"]["available"] and engines["fake"]["available"]
    assert not engines["antigravity"]["available"], "no worker reported it"
    assert engines["antigravity"]["reason"] == "No running worker serves this engine"
    assert body["default"] == "claude_code"


def test_two_workers_report_their_own_engines(client, login):
    docker_worker = [EngineHealth(name="claude_code", available=True), EngineHealth(name="fake", available=True)]
    host_worker = [EngineHealth(name="antigravity", available=True, reason="Uses the agy account login")]
    asyncio.run(_redis_call(lambda r: EngineHealthStore(r).publish(docker_worker)))
    asyncio.run(_redis_call(lambda r: EngineHealthStore(r).publish(host_worker)))

    body = client.get("/api/v1/engines", headers=_headers(login)).json()

    assert {e["name"]: e["available"] for e in body["engines"]} == {
        "claude_code": True,
        "antigravity": True,
        "fake": True,
    }


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
