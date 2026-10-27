import json
import uuid
from typing import Annotated, Any

from fastapi import Depends
from pydantic import BaseModel

from src.libs.decorators.transactional_decorator import Transactional
from src.libs.exceptions import ErrorCode, UnprocessableEntityException
from src.libs.ids import new_generation_id
from src.libs.security import ensure_owner
from src.modules.generations.infrastructure.adapters import EngineRegistryDep, EventPublisherDep, JobQueueDep, RedisDep
from src.modules.generations.ports.output import IGenerationRepoDep
from src.modules.shared.domain.backend_spec import validate_spec_data
from src.modules.shared.domain.entities import BackendSpecEntity, FrontendSpecEntity, GenerationEntity, UserEntity
from src.modules.shared.domain.enums import GenerationMode, SpecSource
from src.modules.shared.domain.frontend_spec import validate_frontend_spec_data
from src.modules.shared.domain.generation_modes import initial_lanes
from src.modules.specs.ports.output import IBackendSpecRepoDep, IFrontendSpecRepoDep

IDEMPOTENCY_TTL_S = 24 * 3600
NEEDS_BACKEND = {GenerationMode.BACKEND, GenerationMode.DYNAMIC}
NEEDS_FRONTEND = {GenerationMode.STATIC, GenerationMode.DYNAMIC}
EXPECTED_INPUTS = {
    GenerationMode.BACKEND: "'backendSpec' or 'specId'",
    GenerationMode.STATIC: "'frontendSpec' or 'frontendSpecId'",
    GenerationMode.DYNAMIC: "one of 'frontendSpec' / 'frontendSpecId' and one of 'backendSpec' / 'specId'",
}


class GenerationInputs(BaseModel):
    mode: GenerationMode = GenerationMode.BACKEND
    backend_spec: dict[str, Any] | None = None
    spec_id: uuid.UUID | None = None
    frontend_spec: dict[str, Any] | None = None
    frontend_spec_id: uuid.UUID | None = None

    def check(self) -> None:
        """Story 12.2: exactly the inputs the mode needs, else 422 MODE_INPUT_MISMATCH."""
        backend = [value for value in (self.backend_spec, self.spec_id) if value is not None]
        frontend = [value for value in (self.frontend_spec, self.frontend_spec_id) if value is not None]
        ok = len(backend) == (1 if self.mode in NEEDS_BACKEND else 0) and len(frontend) == (
            1 if self.mode in NEEDS_FRONTEND else 0
        )
        if not ok:
            raise UnprocessableEntityException(
                f"Mode '{self.mode}' takes exactly {EXPECTED_INPUTS[self.mode]}",
                code=ErrorCode.MODE_INPUT_MISMATCH,
            )
        declared = (self.frontend_spec or {}).get("project", {}) if isinstance(self.frontend_spec, dict) else {}
        spec_mode = declared.get("mode") if isinstance(declared, dict) else None
        if isinstance(spec_mode, str) and spec_mode != self.mode:
            raise self.mode_mismatch(spec_mode)

    def mode_mismatch(self, spec_mode: str) -> UnprocessableEntityException:
        return UnprocessableEntityException(
            f"The FrontendSpec is for a '{spec_mode}' site but the generation mode is '{self.mode}'",
            code=ErrorCode.MODE_INPUT_MISMATCH,
        )


class CreateGenerationUsecase:
    def __init__(
        self,
        generation_repo: IGenerationRepoDep,
        spec_repo: IBackendSpecRepoDep,
        frontend_spec_repo: IFrontendSpecRepoDep,
        queue: JobQueueDep,
        events: EventPublisherDep,
        registry: EngineRegistryDep,
        redis: RedisDep,
    ):
        self.generation_repo = generation_repo
        self.spec_repo = spec_repo
        self.frontend_spec_repo = frontend_spec_repo
        self.queue = queue
        self.events = events
        self.registry = registry
        self.redis = redis

    async def execute(
        self,
        user: UserEntity,
        inputs: GenerationInputs,
        options: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> GenerationEntity:
        inputs.check()
        if options.get("deployPreview") and not options.get("generateDockerfile") and inputs.mode in NEEDS_BACKEND:
            raise UnprocessableEntityException(
                "deployPreview requires generateDockerfile", code=ErrorCode.OPTIONS_CONFLICT
            )
        engine = options.get("engine") or self.registry.default
        if engine not in self.registry.names():
            raise UnprocessableEntityException(f"Engine '{engine}' is not enabled", code=ErrorCode.ENGINE_UNKNOWN)
        options = {**options, "engine": engine}
        if inputs.mode in NEEDS_FRONTEND:
            options["frontend"] = options.get("frontend") or {
                "runTests": True,
                "generatePreview": True,
                "mockApi": True,
            }
        else:
            options.pop("frontend", None)

        idempotency_redis_key = f"bga:idem:{user.id}:{idempotency_key}" if idempotency_key else None
        if idempotency_redis_key:
            existing_id = await self.redis.get(idempotency_redis_key)
            existing = self.generation_repo.find_by_id(existing_id) if existing_id else None
            if existing is not None:
                return existing

        generation = await self._persist(user, inputs, options, engine)
        if idempotency_redis_key:
            await self.redis.set(idempotency_redis_key, generation.id, ex=IDEMPOTENCY_TTL_S, nx=True)
        # Enqueued only after the commit, so the worker can always see the row it is handed.
        await self.queue.enqueue(generation.id, generation.engine)
        await self.events.publish(
            generation.id,
            "status.changed",
            status=generation.status,
            payload={"engine": engine, "mode": generation.mode, "lanes": generation.lanes},
        )
        return generation

    @Transactional
    async def _persist(self, user, inputs: GenerationInputs, options, engine) -> GenerationEntity:
        backend = self._backend_spec(user, inputs) if inputs.mode in NEEDS_BACKEND else None
        frontend = self._frontend_spec(user, inputs) if inputs.mode in NEEDS_FRONTEND else None
        return self.generation_repo.create(
            GenerationEntity(
                id=new_generation_id(),
                owner_id=user.id,
                mode=inputs.mode,
                spec_id=backend.id if backend else None,
                frontend_spec_id=frontend.id if frontend else None,
                lanes=initial_lanes(inputs.mode),
                options=options,
                engine=engine,
            )
        )

    def _backend_spec(self, user: UserEntity, inputs: GenerationInputs) -> BackendSpecEntity:
        if inputs.spec_id is not None:
            spec = self.spec_repo.find_by_id(inputs.spec_id)
            if spec is None:
                raise UnprocessableEntityException("specId does not exist", code=ErrorCode.VALIDATION_ERROR)
            ensure_owner(spec.owner_id, user.id, user.is_admin, resource="BackendSpec")
            return spec
        # Invalid inline specs are accepted on purpose: the first node reports them as a FAILED job.
        backend_spec = inputs.backend_spec
        result = validate_spec_data(backend_spec)
        version = backend_spec.get("specVersion")
        return self.spec_repo.create(
            BackendSpecEntity(
                owner_id=user.id,
                spec_version=version if isinstance(version, str) else "unknown",
                raw_json=json.dumps(backend_spec, ensure_ascii=False, indent=2),
                normalized_json=result.normalized,
                source=SpecSource.JSON,
            )
        )

    def _frontend_spec(self, user: UserEntity, inputs: GenerationInputs) -> FrontendSpecEntity:
        if inputs.frontend_spec_id is not None:
            spec = self.frontend_spec_repo.find_by_id(inputs.frontend_spec_id)
            if spec is None:
                raise UnprocessableEntityException("frontendSpecId does not exist", code=ErrorCode.VALIDATION_ERROR)
            ensure_owner(spec.owner_id, user.id, user.is_admin, resource="FrontendSpec")
            if spec.mode is not None and spec.mode != inputs.mode:
                raise inputs.mode_mismatch(spec.mode)
            return spec
        frontend_spec = inputs.frontend_spec
        result = validate_frontend_spec_data(frontend_spec)
        version = frontend_spec.get("specVersion")
        return self.frontend_spec_repo.create(
            FrontendSpecEntity(
                owner_id=user.id,
                spec_version=version if isinstance(version, str) else "unknown",
                mode=result.normalized["project"]["mode"] if result.normalized else None,
                raw_json=json.dumps(frontend_spec, ensure_ascii=False, indent=2),
                normalized_json=result.normalized,
                source=SpecSource.JSON,
            )
        )


CreateGenerationUsecaseDep = Annotated[CreateGenerationUsecase, Depends(CreateGenerationUsecase)]
