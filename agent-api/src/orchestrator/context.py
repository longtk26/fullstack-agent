import asyncio
import uuid
from pathlib import Path
from typing import Any

from src.configs import config, get_logger
from src.engines import (
    EngineContext,
    EngineEvent,
    EngineRequest,
    EngineResult,
    EngineStatus,
    ICodeEngine,
    PromptLibrary,
    RenderedPrompt,
)
from src.modules.generations.infrastructure.adapters import EventPublisher
from src.modules.shared.domain.entities import CliInvocationEntity
from src.modules.shared.domain.enums import GenerationStatus

from .state import status_for
from .store import JobStore
from .validation import IValidationRunner
from .workspace import JobWorkspace, WorkspaceManager

logger = get_logger(__name__)


class JobCancelled(Exception):
    pass


class EngineFailure(Exception):
    def __init__(self, result: EngineResult):
        super().__init__(f"{result.engine} {result.purpose}: {result.status} ({result.error_reason})")
        self.result = result


class JobContext:
    """Everything a node needs for one generation; nodes stay plain functions of (state, ctx)."""

    def __init__(
        self,
        generation_id: str,
        engine: ICodeEngine,
        engine_context: EngineContext,
        prompts: PromptLibrary,
        validator: IValidationRunner,
        store: JobStore,
        events: EventPublisher,
        workspaces: WorkspaceManager,
        workspace: JobWorkspace,
    ):
        self.generation_id = generation_id
        self.engine = engine
        self.engine_context = engine_context
        self.prompts = prompts
        self.validator = validator
        self.store = store
        self.events = events
        self.workspaces = workspaces
        self.workspace = workspace
        self.cancel_requested = asyncio.Event()
        self.current_invocation: str | None = None
        self._status: GenerationStatus | None = None

    async def emit(self, type: str, step: str | None = None, status: str | None = None, **payload: Any) -> None:
        await self.events.publish(self.generation_id, type, step=step, status=status, payload=payload)

    async def set_status(
        self, status: GenerationStatus, step: str | None = None, payload: dict[str, Any] | None = None, **fields: Any
    ) -> None:
        self.store.update_generation(self.generation_id, status=status, **fields)
        if status != self._status:
            self._status = status
            await self.emit("status.changed", step=step, status=status, **(payload or {}))

    async def check_cancel(self) -> None:
        if not self.cancel_requested.is_set():
            generation = self.store.generation(self.generation_id)
            if generation is not None and generation.cancel_requested:
                self.cancel_requested.set()
        if self.cancel_requested.is_set():
            raise JobCancelled()

    async def request_cancel(self) -> None:
        self.cancel_requested.set()
        if self.current_invocation:
            await self.engine.cancel(self.current_invocation)

    async def enter_node(self, node: str, attempt: int) -> uuid.UUID:
        await self.check_cancel()
        await self.set_status(status_for(node), step=node, current_step=node)
        run_id = self.store.start_node(self.generation_id, node, attempt)
        await self.emit("step.started", step=node, attempt=attempt)
        return run_id

    async def leave_node(self, node: str, run_id: uuid.UUID, status: str, summary: dict[str, Any]) -> None:
        self.store.finish_node(run_id, status, summary)
        await self.emit("step.finished", step=node, status=status, **summary)

    async def run_engine(self, node: str, purpose: str, prompt: RenderedPrompt) -> EngineResult:
        await self.check_cancel()
        await self.engine.prepare_workspace(self.workspace.project, self.engine_context)
        request = EngineRequest(
            purpose=purpose,
            workdir=self.workspace.project,
            state_dir=self.workspace.state,
            prompt=prompt.text,
            prompt_ref=prompt.ref,
            max_turns=config.engine_max_turns,
            timeout_s=config.engine_timeout_seconds,
        )
        record_id = self.store.add_cli_invocation(
            CliInvocationEntity(
                generation_id=self.generation_id,
                engine=self.engine.name,
                purpose=purpose,
                status="running",
            )
        )
        await self.emit("engine.started", step=node, engine=self.engine.name, purpose=purpose, prompt=prompt.ref.id)

        async def forward(event: EngineEvent) -> None:
            await self.emit("engine.event", step=node, kind=event.kind, summary=event.summary)

        self.current_invocation = request.invocation_id
        try:
            result = await self.engine.run(request, forward)
        finally:
            self.current_invocation = None
        usage = result.usage
        self.store.update_cli_invocation(
            record_id,
            status=result.status,
            exit_code=result.exit_code,
            duration_ms=result.duration_ms,
            turns=result.turns,
            input_tokens=usage.input_tokens if usage else None,
            output_tokens=usage.output_tokens if usage else None,
            cost_usd=usage.cost_usd if usage else None,
            argv_redacted=result.argv_redacted,
            stdout_ref=result.stdout_ref,
            stderr_ref=result.stderr_ref,
        )
        await self.emit(
            "engine.finished",
            step=node,
            status=result.status,
            purpose=purpose,
            errorReason=result.error_reason,
            durationMs=result.duration_ms,
            turns=result.turns,
            usage=usage.model_dump() if usage else None,
            changedFiles=result.changed_files[:50],
        )
        if result.status == EngineStatus.CANCELLED or self.cancel_requested.is_set():
            raise JobCancelled()
        if result.status != EngineStatus.OK:
            raise EngineFailure(result)
        return result

    def file_tree(self, limit: int = 300) -> str:
        project = self.workspace.project
        skip = {".git", ".claude", ".agents", "__pycache__", ".venv"}
        files = sorted(
            p.relative_to(project).as_posix()
            for p in project.rglob("*")
            if p.is_file() and not any(part in skip for part in p.relative_to(project).parts)
        )
        shown = files[:limit]
        more = f"\n… and {len(files) - limit} more" if len(files) > limit else ""
        return ("\n".join(shown) or "(empty project)") + more

    def project_path(self, *parts: str) -> Path:
        return self.workspace.project.joinpath(*parts)
