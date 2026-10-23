from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from src.engines import EngineRegistry, get_engine_registry
from src.libs.queue import JobQueue
from src.libs.redaction import default_redactor
from src.libs.redis import get_redis

from .event_publisher import EventPublisher

RedisDep = Annotated[Redis, Depends(get_redis)]


def get_job_queue() -> JobQueue:
    return JobQueue(get_redis())


def get_event_publisher() -> EventPublisher:
    return EventPublisher(get_redis(), default_redactor())


JobQueueDep = Annotated[JobQueue, Depends(get_job_queue)]
EventPublisherDep = Annotated[EventPublisher, Depends(get_event_publisher)]
EngineRegistryDep = Annotated[EngineRegistry, Depends(get_engine_registry)]
