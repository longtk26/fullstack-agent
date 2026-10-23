import asyncio
import shutil
import time
from pathlib import Path

from pydantic import BaseModel

from .port import (
    EngineContext,
    EngineErrorReason,
    EngineEvent,
    EngineEventKind,
    EngineHealth,
    EngineRequest,
    EngineResult,
    EngineStatus,
    EngineUsage,
    ICodeEngine,
    OnEngineEvent,
)
from .workspace import changed_files, ensure_inside, install_skills, snapshot, write_managed_section


class FakeStep(BaseModel):
    """One scripted engine call: files to write/copy/delete, an optional delay, and the outcome to report."""

    write: dict[str, str] = {}
    copy_from: Path | None = None
    delete: list[str] = []
    sleep_s: float = 0
    status: EngineStatus = EngineStatus.OK
    error_reason: EngineErrorReason | None = None
    message: str = "Done."


DEFAULT_SCENARIO = {"*": [FakeStep(write={"FAKE_ENGINE.md": "Written by the fake engine.\n"})]}


class FakeEngine(ICodeEngine):
    """Deterministic engine for tests and UI work: replays FakeSteps per purpose, never calls a model.

    Each call for a purpose consumes the next step; the last step repeats. Purpose "*" is the fallback.
    """

    name = "fake"

    def __init__(self, allowed_root: Path, scenario: dict[str, list[FakeStep]] | None = None):
        self.allowed_root = allowed_root
        self.scenario = {purpose: list(steps) for purpose, steps in (scenario or DEFAULT_SCENARIO).items()}
        self.calls: list[EngineRequest] = []
        self._cancels: dict[str, asyncio.Event] = {}

    async def health(self) -> EngineHealth:
        return EngineHealth(name=self.name, available=True, reason="Scripted engine; no model calls")

    async def prepare_workspace(self, workdir: Path, context: EngineContext) -> None:
        install_skills(context.skill_dirs, workdir / ".claude" / "skills")
        write_managed_section(workdir / "CLAUDE.md", context.conventions)

    async def cancel(self, invocation_id: str) -> bool:
        event = self._cancels.get(invocation_id)
        if event is None:
            return False
        event.set()
        return True

    def _next_step(self, purpose: str) -> FakeStep:
        steps = self.scenario.get(purpose) or self.scenario.get("*") or [FakeStep()]
        return steps.pop(0) if len(steps) > 1 else steps[0]

    async def run(self, request: EngineRequest, on_event: OnEngineEvent | None = None) -> EngineResult:
        workdir = ensure_inside(request.workdir, self.allowed_root)
        ensure_inside(request.state_dir, self.allowed_root)
        self.calls.append(request)
        step = self._next_step(request.purpose)
        started = time.monotonic()
        before = snapshot(workdir)

        async def emit(kind: EngineEventKind, summary: str, **data) -> None:
            if on_event is not None:
                await on_event(EngineEvent(kind=kind, summary=summary, data=data))

        await emit(EngineEventKind.SYSTEM, "session started (fake)")
        cancel = self._cancels.setdefault(request.invocation_id, asyncio.Event())
        status, reason = step.status, step.error_reason
        try:
            if step.sleep_s:
                try:
                    await asyncio.wait_for(cancel.wait(), timeout=step.sleep_s)
                    status, reason = EngineStatus.CANCELLED, EngineErrorReason.CANCELLED
                except TimeoutError:
                    pass
            if status != EngineStatus.CANCELLED:
                if step.copy_from is not None:
                    shutil.copytree(step.copy_from, workdir, dirs_exist_ok=True)
                    await emit(EngineEventKind.TOOL_USE, f"Copy {step.copy_from.name}", tool="Copy")
                for relative, content in step.write.items():
                    target = ensure_inside(workdir / relative, workdir)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content)
                    await emit(EngineEventKind.TOOL_USE, f"Write {relative}", tool="Write", target=relative)
                    await emit(EngineEventKind.TOOL_RESULT, "ok: written", isError=False)
                for relative in step.delete:
                    ensure_inside(workdir / relative, workdir).unlink(missing_ok=True)
                    await emit(EngineEventKind.TOOL_USE, f"Delete {relative}", tool="Delete", target=relative)
                await emit(EngineEventKind.MESSAGE, step.message)
        finally:
            self._cancels.pop(request.invocation_id, None)

        usage = EngineUsage(input_tokens=1000, output_tokens=200, cost_usd=0.0)
        await emit(EngineEventKind.USAGE, "1 turns, 200 output tokens", **usage.model_dump())
        return EngineResult(
            invocation_id=request.invocation_id,
            engine=self.name,
            purpose=request.purpose,
            status=status,
            error_reason=reason,
            error_message=None if status == EngineStatus.OK else f"fake {status}",
            exit_code=0 if status == EngineStatus.OK else 1,
            duration_ms=int((time.monotonic() - started) * 1000),
            turns=1,
            usage=usage,
            session_id=f"fake-{request.invocation_id}",
            final_message=step.message,
            changed_files=changed_files(before, snapshot(workdir)),
            argv_redacted=["fake"],
            prompt_ref=request.prompt_ref,
        )
