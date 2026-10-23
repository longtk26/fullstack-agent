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
    crash: bool = False
    status: EngineStatus = EngineStatus.OK
    error_reason: EngineErrorReason | None = None
    message: str = "Done."


class SimulatedCrash(BaseException):
    """Escapes normal error handling, like a worker dying mid-step (for recovery tests)."""


_ROUTER = "src/modules/demo/presenter/router.py"


def demo_scenario(delay_s: float = 0.3) -> dict[str, list[FakeStep]]:
    """Walks the whole workflow including one repair: the first router is broken on purpose."""
    return {
        "generate_database": [
            FakeStep(
                sleep_s=delay_s,
                write={
                    "src/modules/shared/domain/entities/demo_entity.py": (
                        "from pydantic import BaseModel\n\n\nclass DemoEntity(BaseModel):\n    name: str\n"
                    )
                },
            )
        ],
        "generate_backend": [
            FakeStep(
                sleep_s=delay_s,
                write={_ROUTER: "from fastapi import APIRouter\n\ndemo_router = APIRouter(\n\ndef broken(:\n"},
            )
        ],
        "generate_tests": [
            FakeStep(sleep_s=delay_s, write={"tests/test_demo.py": "def test_demo():\n    assert True\n"})
        ],
        "repair_code": [
            FakeStep(
                sleep_s=delay_s,
                write={_ROUTER: 'from fastapi import APIRouter\n\ndemo_router = APIRouter(prefix="/demo")\n'},
                message="Fixed the syntax error in the demo router.",
            )
        ],
        "*": [FakeStep(write={"FAKE_ENGINE.md": "Written by the fake engine.\n"})],
    }


DEMO_SCENARIO = demo_scenario()
DEFAULT_SCENARIO = DEMO_SCENARIO


class FakeEngine(ICodeEngine):
    """Deterministic engine for tests and UI work: replays FakeSteps per purpose, never calls a model.

    Calls are counted per (workspace, purpose): the n-th call gets the n-th step and the last step repeats,
    so concurrent jobs never consume each other's script. Purpose "*" is the fallback.
    """

    name = "fake"

    def __init__(self, allowed_root: Path, scenario: dict[str, list[FakeStep]] | None = None):
        self.allowed_root = allowed_root
        self.scenario = {purpose: list(steps) for purpose, steps in (scenario or DEFAULT_SCENARIO).items()}
        self.calls: list[EngineRequest] = []
        self._counts: dict[tuple[str, str], int] = {}
        self._cancels: dict[str, asyncio.Event] = {}

    async def health(self) -> EngineHealth:
        return EngineHealth(name=self.name, available=True, reason="Scripted engine; no model calls")

    async def prepare_workspace(self, workdir: Path, context: EngineContext) -> None:
        install_skills(context.skill_dirs, workdir / ".claude" / "skills")
        write_managed_section(workdir / "CLAUDE.md", context.conventions)

    async def cancel(self, invocation_id: str) -> bool:
        # setdefault, not get: a cancel that lands just before run() registers the invocation must not be lost.
        self._cancels.setdefault(invocation_id, asyncio.Event()).set()
        return True

    def _next_step(self, workdir: Path, purpose: str) -> FakeStep:
        steps = self.scenario.get(purpose) or self.scenario.get("*") or [FakeStep()]
        key = (str(workdir), purpose)
        index = self._counts.get(key, 0)
        self._counts[key] = index + 1
        return steps[min(index, len(steps) - 1)]

    async def run(self, request: EngineRequest, on_event: OnEngineEvent | None = None) -> EngineResult:
        workdir = ensure_inside(request.workdir, self.allowed_root)
        ensure_inside(request.state_dir, self.allowed_root)
        self.calls.append(request)
        step = self._next_step(workdir, request.purpose)
        if step.crash:
            raise SimulatedCrash(f"simulated crash during {request.purpose}")
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
