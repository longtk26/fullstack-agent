from contextlib import asynccontextmanager
from pathlib import Path

from src.configs import config
from src.engines import PromptLibrary, build_engine_context, get_engine_registry
from src.libs.queue import JobQueue, PreviewCommandBus
from src.libs.redaction import default_redactor
from src.libs.redis import get_redis
from src.modules.generations.infrastructure.adapters import EventPublisher
from src.preview.docker_preview import DockerPreviewRuntime
from src.sandbox import DockerSandboxProvider

from .checkpointer import postgres_checkpointer
from .previews import PreviewService
from .runner import JobRunner
from .store import JobStore
from .validation import SandboxValidationRunner, StaticValidationRunner
from .worker_service import WorkerService, default_worker_id
from .workspace import WorkspaceManager


@asynccontextmanager
async def build_worker_service(worker_id: str | None = None):
    redis = get_redis()
    registry = get_engine_registry()
    prompts = PromptLibrary()
    store = JobStore()
    events = EventPublisher(redis, default_redactor(), cap=config.events_cap)
    workspaces = WorkspaceManager(Path(config.workspace_root), config.workspace_max_mb)
    worker_id = worker_id or default_worker_id()
    sandboxes = DockerSandboxProvider() if config.sandbox_enabled else None
    previews = (
        PreviewService(DockerPreviewRuntime(), store, events, PreviewCommandBus(redis))
        if config.preview_enabled
        else None
    )
    async with postgres_checkpointer() as checkpointer:
        runner = JobRunner(
            registry=registry,
            checkpointer=checkpointer,
            store=store,
            events=events,
            workspaces=workspaces,
            prompts=prompts,
            validator=SandboxValidationRunner() if sandboxes else StaticValidationRunner(),
            engine_context=build_engine_context(prompts),
            worker_id=worker_id,
            sandboxes=sandboxes,
            template_dir=Path(config.template_dir),
            on_completed=previews.request_start if previews else None,
        )
        # Every worker requests previews for its finished jobs; only a preview worker drives the containers.
        yield WorkerService(
            runner,
            JobQueue(redis),
            store,
            events,
            redis,
            registry,
            workspaces,
            worker_id,
            previews=previews if config.preview_worker else None,
        )
