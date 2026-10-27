import asyncio
import re
import uuid
from datetime import UTC, datetime, timedelta
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
    ModelCall,
    PromptLibrary,
    RenderedPrompt,
)
from src.libs.redaction import default_redactor
from src.modules.generations.infrastructure.adapters import EventPublisher
from src.modules.shared.domain.entities import CliInvocationEntity, ModelCallEntity, SandboxExecEntity
from src.modules.shared.domain.enums import GenerationMode, GenerationStatus, LaneStatus
from src.sandbox import ExecResult, ISandbox, ISandboxProvider

from . import tracing
from .state import NODE_LANE, lane_status_for, status_for
from .store import JobStore
from .validation import IValidationRunner
from .workspace import JobWorkspace, WorkspaceManager

logger = get_logger(__name__)
PROVIDERS = {"claude_code": "anthropic", "antigravity": "google"}
_TOOL_SCRIPT = re.compile(r"/opt/bga/bin/([\w-]+)")


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
        sandboxes: ISandboxProvider | None = None,
        template_dir: Path | None = None,
        mode: GenerationMode = GenerationMode.BACKEND,
        lanes: dict[str, str] | None = None,
        frontend_engine_context: EngineContext | None = None,
        frontend_validator: Any = None,
    ):
        self.generation_id = generation_id
        self.mode = mode
        self.lanes: dict[str, str] = dict(lanes or {})
        self.current_lane: str | None = None
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
        self.current_run_id: uuid.UUID | None = None
        self.sandboxes = sandboxes
        self.template_dir = template_dir or Path(config.template_dir)
        self._sandbox: ISandbox | None = None
        self._frontend_sandbox: ISandbox | None = None
        self.frontend_engine_context = frontend_engine_context or engine_context
        self.frontend_validator = frontend_validator
        self._status: GenerationStatus | None = None
        self.trace: tracing.GenerationTrace | None = None

    async def emit(self, type: str, step: str | None = None, status: str | None = None, **payload: Any) -> None:
        await self.events.publish(
            self.generation_id, type, step=step, status=status, payload=payload, lane=self.current_lane
        )

    async def set_status(
        self, status: GenerationStatus, step: str | None = None, payload: dict[str, Any] | None = None, **fields: Any
    ) -> None:
        self.store.update_generation(self.generation_id, status=status, **fields)
        if status != self._status:
            self._status = status
            await self.emit("status.changed", step=step, status=status, **(payload or {}), lanes=self.lanes)

    async def set_lane(self, lane: str, status: LaneStatus, reason: str | None = None) -> None:
        """Story 12.2: one status per lane, stored on the generation and announced as `lane.changed`."""
        if lane not in self.lanes or self.lanes[lane] == status.value:
            return
        self.lanes[lane] = status.value
        self.store.update_generation(self.generation_id, lanes=dict(self.lanes))
        payload: dict[str, Any] = {"lanes": dict(self.lanes)}
        if reason:
            payload["reason"] = reason
        await self.events.publish(self.generation_id, "lane.changed", status=status.value, payload=payload, lane=lane)

    async def replace_lanes(self, lanes: dict[str, str]) -> None:
        for lane, status in lanes.items():
            await self.set_lane(lane, LaneStatus(status))

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
        lane = NODE_LANE.get(node)
        self.current_lane = lane.value if lane else None
        if lane is not None:
            await self.set_lane(lane.value, lane_status_for(node))
        await self.set_status(status_for(node), step=node, current_step=node)
        run_id = self.store.start_node(self.generation_id, node, attempt)
        self.current_run_id = run_id
        await self.emit("step.started", step=node, attempt=attempt)
        return run_id

    async def leave_node(self, node: str, run_id: uuid.UUID, status: str, summary: dict[str, Any]) -> None:
        self.store.finish_node(run_id, status, summary)
        await self.emit("step.finished", step=node, status=status, **summary)

    async def run_engine(self, node: str, purpose: str, prompt: RenderedPrompt, repo: str = "project") -> EngineResult:
        """One engine call in the backend project (`repo="project"`) or the frontend (`repo="frontend"`), each
        with its own skill and project rules."""
        await self.check_cancel()
        workdir = self.workspace.repo(repo)
        context = self.frontend_engine_context if repo == "frontend" else self.engine_context
        await self.engine.prepare_workspace(workdir, context)
        request = EngineRequest(
            purpose=purpose,
            workdir=workdir,
            state_dir=self.workspace.state,
            prompt=prompt.text,
            prompt_ref=prompt.ref,
        )
        prompt_id = f"{prompt.ref.id}@{prompt.ref.version}"
        record_id = self.store.add_cli_invocation(
            CliInvocationEntity(
                generation_id=self.generation_id,
                node_run_id=self.current_run_id,
                engine=self.engine.name,
                purpose=purpose,
                status="running",
                prompt_ref=prompt_id,
            )
        )
        await self.emit("engine.started", step=node, engine=self.engine.name, purpose=purpose, prompt=prompt.ref.id)
        engine_span = tracing.current().child(
            f"engine:{self.engine.name}",
            "tool",
            inputs={
                "purpose": purpose,
                "prompt": prompt_id,
                "promptSha256": prompt.ref.sha256,
                "workdir": repo,
                "maxTurns": request.max_turns,
            },
            metadata={"engine": self.engine.name, "purpose": purpose},
        )

        async def forward(event: EngineEvent) -> None:
            await self.emit("engine.event", step=node, kind=event.kind, summary=event.summary)

        self.current_invocation = request.invocation_id
        try:
            result = await self.engine.run(request, forward)
        except BaseException as exc:
            engine_span.end(error=f"{type(exc).__name__}: {exc}"[:500])
            raise
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
            cache_read_tokens=usage.cache_read_tokens if usage else None,
            cache_write_tokens=usage.cache_write_tokens if usage else None,
            thinking_tokens=usage.thinking_tokens if usage else None,
            cost_usd=usage.cost_usd if usage else None,
            cost_source=usage.cost_source if usage else None,
            model=(usage.model if usage else None) or next((c.model for c in result.model_calls if c.model), None),
            error_reason=result.error_reason,
            changed_files=[default_redactor().redact(path) for path in result.changed_files[:200]],
            finished_at=datetime.now(UTC),
            argv_redacted=result.argv_redacted,
            stdout_ref=result.stdout_ref,
            stderr_ref=result.stderr_ref,
        )
        self._record_model_calls(record_id, result.model_calls, engine_span)
        engine_span.end(
            outputs={
                "status": result.status,
                "exitCode": result.exit_code,
                "durationMs": result.duration_ms,
                "turns": result.turns,
                "usage": usage.model_dump() if usage else None,
                "costUsd": usage.cost_usd if usage else None,
                "modelCalls": len(result.model_calls),
                "toolsDropped": result.tools_dropped,
                "changedFiles": result.changed_files[:50],
            },
            error=None if result.ok else f"{result.status}: {result.error_message or result.error_reason}",
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

    def _record_model_calls(self, invocation_id: uuid.UUID, calls: list[ModelCall], parent: tracing.Span) -> None:
        """Stores the model calls (Story 8.4) and hangs them, with their tools, under the engine span."""
        redactor = default_redactor()
        for call in calls:
            for tool in call.tools:
                tool.target = redactor.redact(tool.target)  # span names are not covered by the client's hooks
        self.store.add_model_calls(
            [
                ModelCallEntity(
                    generation_id=self.generation_id,
                    cli_invocation_id=invocation_id,
                    node_run_id=self.current_run_id,
                    lane=self.current_lane or "backend",
                    duration_ms=call.duration_ms,
                    tools=[tool.model_dump(mode="json") for tool in call.tools],
                    **call.model_dump(exclude={"tools"}),
                )
                for call in calls
            ]
        )
        provider = PROVIDERS.get(self.engine.name, self.engine.name)
        for call in calls:
            llm = parent.child(
                f"llm:{call.model or 'unknown'} #{call.seq}",
                "llm",
                inputs={"seq": call.seq},
                metadata={
                    "ls_model_name": call.model,
                    "ls_provider": provider,
                    "cost_source": call.cost_source,
                    "latency_source": call.latency_source,
                },
                start_time=call.started_at,
                end_time=call.ended_at,
            )
            for tool in call.tools:
                ended = tool.ended_at or tool.started_at
                llm.child(
                    f"tool:{tool.name} {tool.target}".strip(),
                    "tool",
                    inputs={"target": tool.target},
                    start_time=tool.started_at,
                    end_time=ended,
                ).end(outputs={"isError": tool.is_error}, error="tool error" if tool.is_error else None, end_time=ended)
            usage: dict[str, Any] = {
                "input_tokens": call.input_tokens,
                "output_tokens": call.output_tokens,
                "total_tokens": call.input_tokens + call.output_tokens,
                "input_token_details": {
                    "cache_read": call.cache_read_tokens,
                    "cache_creation": call.cache_write_tokens,
                },
            }
            if call.thinking_tokens is not None:
                usage["output_token_details"] = {"reasoning": call.thinking_tokens}
            if call.cost_usd is not None:
                usage["total_cost"] = call.cost_usd
            llm.end(
                outputs={"tools": [tool.name for tool in call.tools], "costSource": call.cost_source},
                usage=usage,
                end_time=call.ended_at,
            )

    @property
    def sandbox_enabled(self) -> bool:
        return self.sandboxes is not None

    async def sandbox(self) -> ISandbox | None:
        """The job's sandbox, started on first use and kept until the job ends (close_sandbox)."""
        if self.sandboxes is None:
            return None
        if self._sandbox is None:
            self._sandbox = RecordingSandbox(self.sandboxes.for_job(self.generation_id, self.workspace.project), self)
        await self._sandbox.start()
        return self._sandbox

    async def frontend_sandbox(self) -> ISandbox | None:
        """The frontend's Node sandbox (Story 13.4): no database, the shared pnpm store, kept until the job ends."""
        if self.sandboxes is None:
            return None
        if self._frontend_sandbox is None:
            inner = self.sandboxes.for_job(self.generation_id, self.workspace.frontend, kind="frontend")
            self._frontend_sandbox = RecordingSandbox(inner, self)
        await self._frontend_sandbox.start()
        return self._frontend_sandbox

    async def close_sandbox(self) -> None:
        for attribute in ("_sandbox", "_frontend_sandbox"):
            sandbox = getattr(self, attribute)
            if sandbox is None:
                continue
            try:
                await sandbox.stop()
            except Exception:
                logger.warning("sandbox cleanup failed", extra={"generation_id": self.generation_id}, exc_info=True)
            setattr(self, attribute, None)

    def file_tree(self, limit: int = 300, repo: str = "project") -> str:
        project = self.workspace.repo(repo)
        skip = {".git", ".claude", ".agents", "__pycache__", ".venv"}
        if repo == "frontend":
            skip |= {"node_modules", ".next", "out", "test-results", "playwright-report"}
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

    def frontend_path(self, *parts: str) -> Path:
        return self.workspace.frontend.joinpath(*parts)


def exec_label(command: str) -> str:
    """`ruff check …` → `ruff check`, `python /opt/bga/bin/startup_check.py` → `startup_check`."""
    script = _TOOL_SCRIPT.search(command)
    if script:
        return script.group(1)
    words = [w for w in command.replace(";", " ").split() if w not in ("set", "-e")]
    if not words:
        return "sh"
    label = words[0].rsplit("/", 1)[-1]
    if len(words) > 1 and words[1].isalpha():
        label += f" {words[1]}"
    return label[:64]


class RecordingSandbox(ISandbox):
    """Records every sandbox command for the local trace and as a `sandbox:*` span (Stories 8.2, 8.3)."""

    def __init__(self, inner: ISandbox, ctx: JobContext):
        self.inner = inner
        self.ctx = ctx
        self._redactor = default_redactor()

    @property
    def db_url(self) -> str:
        return self.inner.db_url

    @property
    def test_db_url(self) -> str:
        return self.inner.test_db_url

    async def start(self) -> None:
        await self.inner.start()

    async def stop(self) -> None:
        await self.inner.stop()

    async def reset_database(self, name: str) -> None:
        await self.inner.reset_database(name)

    async def exec(
        self, command: str, timeout_s: int | None = None, env: dict[str, str] | None = None, egress: bool = False
    ) -> ExecResult:
        started = datetime.now(UTC)
        result = await self.inner.exec(command, timeout_s=timeout_s, env=env, egress=egress)
        name = exec_label(command)
        status = "timeout" if result.timed_out else ("ok" if result.ok else "failed")
        ended = started + timedelta(milliseconds=result.duration_ms)
        try:
            self.ctx.store.add_sandbox_exec(
                SandboxExecEntity(
                    generation_id=self.ctx.generation_id,
                    node_run_id=self.ctx.current_run_id,
                    name=name,
                    command=self._redactor.redact(command)[:500],
                    status=status,
                    exit_code=result.exit_code,
                    started_at=started,
                    duration_ms=result.duration_ms,
                )
            )
        except Exception:  # bookkeeping must not fail the job
            logger.warning("could not record a sandbox exec", extra={"generation_id": self.ctx.generation_id})
        tracing.current().child(
            f"sandbox:{name}", "tool", inputs={"command": command[:500]}, start_time=started, end_time=ended
        ).end(
            outputs={"exitCode": result.exit_code, "durationMs": result.duration_ms, "status": status},
            error=None if result.ok else f"exit {result.exit_code}",
            end_time=ended,
        )
        return result
