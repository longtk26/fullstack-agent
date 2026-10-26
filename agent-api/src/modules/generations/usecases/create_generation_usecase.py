import json
import uuid
from typing import Annotated, Any

from fastapi import Depends

from src.libs.decorators.transactional_decorator import Transactional
from src.libs.exceptions import ErrorCode, UnprocessableEntityException
from src.libs.ids import new_generation_id
from src.libs.security import ensure_owner
from src.modules.generations.infrastructure.adapters import EngineRegistryDep, EventPublisherDep, JobQueueDep, RedisDep
from src.modules.generations.ports.output import IGenerationRepoDep
from src.modules.shared.domain.backend_spec import validate_spec_data
from src.modules.shared.domain.entities import BackendSpecEntity, GenerationEntity, UserEntity
from src.modules.shared.domain.enums import SpecSource
from src.modules.specs.ports.output import IBackendSpecRepoDep

IDEMPOTENCY_TTL_S = 24 * 3600


class CreateGenerationUsecase:
    def __init__(
        self,
        generation_repo: IGenerationRepoDep,
        spec_repo: IBackendSpecRepoDep,
        queue: JobQueueDep,
        events: EventPublisherDep,
        registry: EngineRegistryDep,
        redis: RedisDep,
    ):
        self.generation_repo = generation_repo
        self.spec_repo = spec_repo
        self.queue = queue
        self.events = events
        self.registry = registry
        self.redis = redis

    async def execute(
        self,
        user: UserEntity,
        backend_spec: dict[str, Any] | None,
        spec_id: uuid.UUID | None,
        options: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> GenerationEntity:
        if options.get("deployPreview") and not options.get("generateDockerfile"):
            raise UnprocessableEntityException(
                "deployPreview requires generateDockerfile", code=ErrorCode.OPTIONS_CONFLICT
            )
        engine = options.get("engine") or self.registry.default
        if engine not in self.registry.names():
            raise UnprocessableEntityException(f"Engine '{engine}' is not enabled", code=ErrorCode.ENGINE_UNKNOWN)

        idempotency_redis_key = f"bga:idem:{user.id}:{idempotency_key}" if idempotency_key else None
        if idempotency_redis_key:
            existing_id = await self.redis.get(idempotency_redis_key)
            existing = self.generation_repo.find_by_id(existing_id) if existing_id else None
            if existing is not None:
                return existing

        generation = await self._persist(user, backend_spec, spec_id, {**options, "engine": engine}, engine)
        if idempotency_redis_key:
            await self.redis.set(idempotency_redis_key, generation.id, ex=IDEMPOTENCY_TTL_S, nx=True)
        # Enqueued only after the commit, so the worker can always see the row it is handed.
        await self.queue.enqueue(generation.id, generation.engine)
        await self.events.publish(generation.id, "status.changed", status=generation.status, payload={"engine": engine})
        return generation

    @Transactional
    async def _persist(self, user, backend_spec, spec_id, options, engine) -> GenerationEntity:
        if spec_id is not None:
            spec = self.spec_repo.find_by_id(spec_id)
            if spec is None:
                raise UnprocessableEntityException("specId does not exist", code=ErrorCode.VALIDATION_ERROR)
            ensure_owner(spec.owner_id, user.id, user.is_admin, resource="BackendSpec")
        else:
            # Invalid inline specs are accepted on purpose: validate_spec reports them as a FAILED job.
            result = validate_spec_data(backend_spec)
            version = backend_spec.get("specVersion")
            spec = self.spec_repo.create(
                BackendSpecEntity(
                    owner_id=user.id,
                    spec_version=version if isinstance(version, str) else "unknown",
                    raw_json=json.dumps(backend_spec, ensure_ascii=False, indent=2),
                    normalized_json=result.normalized,
                    source=SpecSource.JSON,
                )
            )
        return self.generation_repo.create(
            GenerationEntity(id=new_generation_id(), owner_id=user.id, spec_id=spec.id, options=options, engine=engine)
        )


CreateGenerationUsecaseDep = Annotated[CreateGenerationUsecase, Depends(CreateGenerationUsecase)]
