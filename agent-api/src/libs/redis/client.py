from functools import lru_cache

from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialBackoff
from redis.exceptions import ConnectionError, TimeoutError

from src.configs import config

# Without a socket timeout, a pooled connection left half-open by a Redis restart blocks a read forever.
# Blocking commands (BLMOVE) use timeouts well below SOCKET_TIMEOUT_S.
SOCKET_TIMEOUT_S = 10


def redis_from_url(url: str) -> Redis:
    return Redis.from_url(
        url,
        decode_responses=True,
        socket_timeout=SOCKET_TIMEOUT_S,
        socket_connect_timeout=5,
        socket_keepalive=True,
        health_check_interval=15,
        retry=Retry(ExponentialBackoff(cap=5, base=0.2), retries=5),
        retry_on_error=[ConnectionError, TimeoutError],
    )


@lru_cache
def get_redis() -> Redis:
    return redis_from_url(config.redis_url)
