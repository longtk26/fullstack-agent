import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path

from src.configs import config, get_logger
from src.engines import EngineContext, EngineRegistry, PromptLibrary, UnknownEngineError
from src.modules.generations.infrastructure.adapters import EventPublisher
from src.modules.shared.domain.enums import GenerationStatus
from src.sandbox import ISandboxProvider, SandboxError

from .context import EngineFailure, JobCancelled, JobContext
from .graph import build_graph
from .nodes import write_artifacts
from .scaffold import TemplateDrift
from .state import GenerationState, Outcome
from .store import JobStore
from .validation import IValidationRunner
from .workspace import DiskLimitExceeded, WorkspaceManager

logger = get_logger(__name__)
TERMINAL = {GenerationStatus.COMPLETED, GenerationStatus.FAILED, GenerationStatus.CANCELLED}


class JobRunner:
    """Runs (or resumes) one generation through the graph and owns its final status."""

    def __init__(
        self,
        registry: EngineRegistry,
        checkpointer,
        store: JobStore,
        events: EventPublisher,
        workspaces: WorkspaceManager,
        prompts: PromptLibrary,
        validator: IValidationRunner,
        engine_context: EngineContext,
        worker_id: str,
        sandboxes: ISandboxProvider | None = None,
        template_dir: Path | None = None,
        on_completed: Callable[[str], Awaitable[None]] | None = None,
    ):
        self.registry = registry
        self.checkpointer = checkpointer
        self.store = store
        self.events = events
        self.workspaces = workspaces
        self.prompts = prompts
        self.validator = validator
        self.engine_context = engine_context
        self.worker_id = worker_id
        self.sandboxes = sandboxes
        self.template_dir = template_dir
        self.on_completed = on_completed  # e.g. deploy the preview (Story 7.3); never affects the job status
        self.active: dict[str, JobContext] = {}

    async def cancel(self, generation_id: str) -> bool:
        ctx = self.active.get(generation_id)
        if ctx is None:
            return False
        await ctx.request_cancel()
        return True

    async def run(self, generation_id: str) -> GenerationStatus | None:
        generation = self.store.generation(generation_id)
        if generation is None or generation.status in TERMINAL:
            return generation.status if generation else None

        workspace = self.workspaces.create(generation_id)
        try:
            engine = self.registry.get(generation.engine)
        except UnknownEngineError as exc:
            return await self._fail_early(generation_id, "ENGINE_UNKNOWN", str(exc))
        health = await engine.health()
        if not health.available:
            return await self._fail_early(generation_id, "ENGINE_UNAVAILABLE", f"{engine.name}: {health.reason}")

        ctx = JobContext(
            generation_id,
            engine,
            self.engine_context,
            self.prompts,
            self.validator,
            self.store,
            self.events,
            self.workspaces,
            workspace,
            sandboxes=self.sandboxes,
            template_dir=self.template_dir,
        )
        ctx._status = generation.status
        if generation.cancel_requested:
            return await self._finish(ctx, GenerationStatus.CANCELLED, None)
        self.active[generation_id] = ctx
        try:
            return await self._execute(ctx, generation, workspace)
        finally:
            await ctx.close_sandbox()
            self.active.pop(generation_id, None)
            self.events.forget(generation_id)

    async def _execute(self, ctx: JobContext, generation, workspace) -> GenerationStatus:
        graph = build_graph(ctx).compile(checkpointer=self.checkpointer)
        run_config = {
            "configurable": {"thread_id": generation.id},
            "run_name": "backend-generation",
            "metadata": {"generation_id": generation.id, "engine": generation.engine},
        }
        snapshot = await graph.aget_state(run_config)
        inputs: GenerationState | None
        if snapshot.values:
            self.store.abandon_running(generation.id)
            if snapshot.values.get("last_commit"):
                self.workspaces.reset_to(workspace, snapshot.values["last_commit"])
            await ctx.emit("job.resumed", resumeCount=generation.resume_count, nextSteps=list(snapshot.next))
            self.store.update_generation(generation.id, worker_id=self.worker_id)
            if not snapshot.next:
                return await self._finish_from_state(ctx, snapshot.values)
            inputs = None
        else:
            self.store.update_generation(generation.id, worker_id=self.worker_id, started_at=datetime.now(UTC))
            await ctx.emit("job.started", engine=generation.engine, options=generation.options)
            inputs = {
                "generation_id": generation.id,
                "spec_id": str(generation.spec_id),
                "engine": generation.engine,
                "options": generation.options,
                "workspace": str(workspace.root),
                "repair_attempts": 0,
                "max_repair_attempts": int(generation.options.get("maxRepairAttempts", 3)),
                "validation": {},
                "failed_checks": [],
                "implicated_files": [],
                "artifact_ids": {},
                "last_commit": self.workspaces.commit(workspace, "job started"),
            }

        try:
            async with asyncio.timeout(generation.options.get("timeoutSeconds") or config.job_timeout_seconds):
                final = await graph.ainvoke(inputs, run_config)
        except JobCancelled:
            return await self._finish(ctx, GenerationStatus.CANCELLED, None)
        except TimeoutError:
            await ctx.request_cancel()
            return await self._finish(ctx, GenerationStatus.FAILED, "Job exceeded its time limit", "TIMEOUT")
        except DiskLimitExceeded as exc:
            return await self._finish(ctx, GenerationStatus.FAILED, str(exc), "DISK_LIMIT")
        except TemplateDrift as exc:
            return await self._finish(ctx, GenerationStatus.FAILED, str(exc)[:500], "TEMPLATE_DRIFT")
        except SandboxError as exc:
            return await self._finish(ctx, GenerationStatus.FAILED, f"Sandbox failed: {exc}"[:500], "SANDBOX_ERROR")
        except EngineFailure as exc:
            message = exc.result.error_message or str(exc)
            return await self._finish(ctx, GenerationStatus.FAILED, f"Engine failed: {message}", "ENGINE_ERROR")
        except asyncio.CancelledError:
            if ctx.cancel_requested.is_set():
                return await self._finish(ctx, GenerationStatus.CANCELLED, None)
            raise  # worker shutdown: leave the job active so it resumes from its checkpoint
        except Exception as exc:
            logger.exception("generation crashed", extra={"generation_id": generation.id})
            return await self._finish(ctx, GenerationStatus.FAILED, f"Internal error: {exc}"[:500], "INTERNAL_ERROR")
        return await self._finish_from_state(ctx, final)

    async def _finish_from_state(self, ctx: JobContext, state: dict) -> GenerationStatus:
        outcome = state.get("outcome")
        if outcome == Outcome.COMPLETED:
            return await self._finish(ctx, GenerationStatus.COMPLETED, None)
        if outcome == Outcome.SPEC_INVALID:
            return await self._finish(ctx, GenerationStatus.FAILED, state.get("error_summary"), "SPEC_INVALID")
        if outcome == Outcome.REPAIR_LIMIT:
            return await self._finish(ctx, GenerationStatus.FAILED, state.get("error_summary"), "REPAIR_LIMIT")
        return await self._finish(ctx, GenerationStatus.FAILED, "Workflow ended without an outcome", "INTERNAL_ERROR")

    async def _finish(
        self, ctx: JobContext, status: GenerationStatus, error: str | None, code: str | None = None
    ) -> GenerationStatus:
        if status == GenerationStatus.FAILED:
            try:
                await write_artifacts(ctx, {}, completed=False, error=error)
            except Exception:  # diagnostics are best effort; the failure itself must still be recorded
                logger.exception("diagnostic packaging failed", extra={"generation_id": ctx.generation_id})
        await ctx.set_status(
            status,
            payload={"errorCode": code, "errorSummary": error},
            error_summary=error,
            finished_at=datetime.now(UTC),
        )
        logger.info("generation finished", extra={"generation_id": ctx.generation_id, "status": status, "code": code})
        generation = self.store.generation(ctx.generation_id)
        if status == GenerationStatus.COMPLETED and self.on_completed and generation.options.get("deployPreview", True):
            try:
                await self.on_completed(ctx.generation_id)
            except Exception:
                logger.exception("preview request failed", extra={"generation_id": ctx.generation_id})
        return status

    async def _fail_early(self, generation_id: str, code: str, message: str) -> GenerationStatus:
        self.store.update_generation(
            generation_id, status=GenerationStatus.FAILED, error_summary=message, finished_at=datetime.now(UTC)
        )
        await self.events.publish(
            generation_id,
            "status.changed",
            status=GenerationStatus.FAILED,
            payload={"errorCode": code, "errorSummary": message},
        )
        return GenerationStatus.FAILED
