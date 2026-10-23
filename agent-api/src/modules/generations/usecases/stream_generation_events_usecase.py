import json
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import Depends
from sqlmodel import Session

from src.libs.database import db_session_manager
from src.libs.queue import events_channel
from src.modules.generations.infrastructure.adapters import RedisDep, event_json
from src.modules.generations.infrastructure.persistence import (
    TERMINAL,
    GenerationEventRepository,
    GenerationRepository,
)
from src.modules.generations.usecases.get_generation_usecase import GetGenerationUsecaseDep
from src.modules.shared.domain.entities import UserEntity

REPLAY_PAGE = 500
IDLE_POLL_S = 5.0  # below the Redis socket timeout
TERMINAL_VALUES = {status.value for status in TERMINAL}


def _is_terminal(event: dict[str, Any]) -> bool:
    return event["type"] == "status.changed" and event.get("status") in TERMINAL_VALUES


class StreamGenerationEventsUsecase:
    """Replays stored events after `after_id`, then tails live ones; ends after the terminal status event.

    It subscribes before replaying, and re-reads the DB when idle, so nothing published in between is lost;
    ids already sent are skipped.
    """

    def __init__(self, getter: GetGenerationUsecaseDep, redis: RedisDep):
        self.getter = getter
        self.redis = redis

    async def execute(self, generation_id: str, user: UserEntity, after_id: int) -> AsyncIterator[dict[str, str]]:
        self.getter.load(generation_id, user)  # 404 before the stream starts
        return self._stream(generation_id, after_id)

    @staticmethod
    def _stored_after(generation_id: str, after_id: int) -> list[dict[str, Any]]:
        with Session(db_session_manager.engine) as session:
            events = GenerationEventRepository(session).list_after(generation_id, after_id, REPLAY_PAGE)
            return [json.loads(event_json(event)) for event in events]

    @staticmethod
    def _is_finished(generation_id: str) -> bool:
        with Session(db_session_manager.engine) as session:
            generation = GenerationRepository(session).find_by_id(generation_id)
            return generation is None or generation.status in TERMINAL

    async def _stream(self, generation_id: str, after_id: int) -> AsyncIterator[dict[str, str]]:
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(events_channel(generation_id))
        last = after_id
        try:
            while True:
                batch = self._stored_after(generation_id, last)
                for event in batch:
                    yield {"id": str(event["id"]), "data": json.dumps(event, ensure_ascii=False)}
                    last = event["id"]
                    if _is_terminal(event):
                        return
                if len(batch) < REPLAY_PAGE:
                    break
            if self._is_finished(generation_id):
                return
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=IDLE_POLL_S)
                events = [json.loads(message["data"])] if message else self._stored_after(generation_id, last)
                for event in events:
                    if event["id"] <= last:
                        continue
                    yield {"id": str(event["id"]), "data": json.dumps(event, ensure_ascii=False)}
                    last = event["id"]
                    if _is_terminal(event):
                        return
                if message is None and not events and self._is_finished(generation_id):
                    return
        finally:
            await pubsub.aclose()


StreamGenerationEventsUsecaseDep = Annotated[StreamGenerationEventsUsecase, Depends(StreamGenerationEventsUsecase)]
