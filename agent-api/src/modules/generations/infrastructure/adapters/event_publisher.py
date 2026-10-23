import json
from typing import Any

from redis.asyncio import Redis
from sqlmodel import Session

from src.configs import get_logger
from src.libs.database import db_session_manager
from src.libs.queue import events_channel
from src.libs.redaction import Redactor
from src.modules.generations.infrastructure.persistence import GenerationEventRepository
from src.modules.shared.domain.entities import GenerationEventEntity

logger = get_logger(__name__)

# Engine chatter is the only event type that can grow without bound; past the cap it is sampled.
SAMPLED_TYPES = {"engine.event"}
SAMPLE_EVERY = 20


class EventPublisher:
    """Persists an event first (so SSE replay is complete), then publishes it for live subscribers."""

    def __init__(self, redis: Redis, redactor: Redactor, cap: int = 5000):
        self.redis = redis
        self.redactor = redactor
        self.cap = cap
        self._counts: dict[str, int] = {}
        self._skipped: dict[str, int] = {}

    def _count(self, session: Session, generation_id: str) -> int:
        if generation_id not in self._counts:
            self._counts[generation_id] = GenerationEventRepository(session).count(generation_id)
        return self._counts[generation_id]

    async def publish(
        self,
        generation_id: str,
        type: str,
        step: str | None = None,
        status: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> GenerationEventEntity | None:
        with Session(db_session_manager.engine) as session:
            if type in SAMPLED_TYPES and self._count(session, generation_id) >= self.cap:
                skipped = self._skipped[generation_id] = self._skipped.get(generation_id, 0) + 1
                if skipped % SAMPLE_EVERY:
                    return None
            event = GenerationEventRepository(session).append(
                GenerationEventEntity(
                    generation_id=generation_id,
                    type=type,
                    step=step,
                    status=status,
                    payload=self.redactor.redact_obj(payload or {}),
                )
            )
            session.commit()
        self._counts[generation_id] = self._counts.get(generation_id, 0) + 1
        try:
            await self.redis.publish(events_channel(generation_id), event_json(event))
        except Exception:  # the DB row is the source of truth; SSE replay will deliver it
            logger.warning("event publish to redis failed", extra={"generation_id": generation_id})
        return event

    def forget(self, generation_id: str) -> None:
        self._counts.pop(generation_id, None)
        self._skipped.pop(generation_id, None)


def event_json(event: GenerationEventEntity) -> str:
    return json.dumps(
        {
            "id": event.id,
            "ts": event.ts.isoformat() if event.ts else None,
            "generationId": event.generation_id,
            "type": event.type,
            "step": event.step,
            "status": event.status,
            "payload": event.payload,
        },
        default=str,
        ensure_ascii=False,
    )
