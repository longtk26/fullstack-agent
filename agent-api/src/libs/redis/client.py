from functools import lru_cache

from redis.asyncio import Redis

from src.configs import config


@lru_cache
def get_redis() -> Redis:
    return Redis.from_url(config.redis_url, decode_responses=True)
