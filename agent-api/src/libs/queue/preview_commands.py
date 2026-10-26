import json
import uuid
from typing import Any

from redis.asyncio import Redis

COMMANDS_KEY = "bga:preview:commands"
REPLY_PREFIX = "bga:preview:reply:"
REPLY_TTL_S = 30


class PreviewCommandTimeout(Exception):
    pass


class PreviewCommandBus:
    """Preview containers are driven only by the worker (it owns the Docker socket); the API sends it commands.
    `send` is fire-and-forget (start, stop, …: the result shows up in the previews row and as events);
    `call` waits for a reply (logs, request log); its timeout stays below the Redis socket timeout."""

    def __init__(self, redis: Redis):
        self.redis = redis

    async def send(self, op: str, generation_id: str, **args: Any) -> None:
        await self.redis.lpush(COMMANDS_KEY, json.dumps({"op": op, "generationId": generation_id, "args": args}))

    async def call(self, op: str, generation_id: str, timeout_s: float = 8, **args: Any) -> Any:
        reply_key = REPLY_PREFIX + uuid.uuid4().hex
        command = {"op": op, "generationId": generation_id, "args": args, "reply": reply_key}
        await self.redis.lpush(COMMANDS_KEY, json.dumps(command))
        result = await self.redis.brpop([reply_key], timeout=timeout_s)
        if result is None:
            raise PreviewCommandTimeout(f"no worker answered '{op}' within {timeout_s:g}s")
        return json.loads(result[1])

    async def next(self, timeout_s: float) -> dict[str, Any] | None:
        result = await self.redis.brpop([COMMANDS_KEY], timeout=timeout_s)
        return json.loads(result[1]) if result else None

    async def reply(self, reply_key: str, payload: Any) -> None:
        await self.redis.lpush(reply_key, json.dumps(payload, default=str))
        await self.redis.expire(reply_key, REPLY_TTL_S)
