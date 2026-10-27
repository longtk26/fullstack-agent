import asyncio
import shutil
import time
from datetime import UTC, datetime
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
    ModelCall,
    OnEngineEvent,
    ToolCall,
)
from .workspace import changed_files, ensure_inside, install_skills, snapshot, write_managed_section


class FakeStep(BaseModel):
    """One scripted engine call: files to write/copy/delete, an optional delay, and the outcome to report."""

    write: dict[str, str] = {}
    copy_from: Path | None = None
    # Frontend lane: copy the golden frontend matching `.bga/frontend-spec.json` (project name), optionally with
    # one planted conventions defect (a hard-coded colour in the shell) so the repair loop runs.
    golden_frontend: bool = False
    plant_frontend_defect: bool = False
    delete: list[str] = []
    sleep_s: float = 0
    crash: bool = False
    status: EngineStatus = EngineStatus.OK
    error_reason: EngineErrorReason | None = None
    message: str = "Done."


class SimulatedCrash(BaseException):
    """Escapes normal error handling, like a worker dying mid-step (for recovery tests)."""


GOLDEN = Path(__file__).resolve().parent / "golden" / "two_entity"
_TASK_ROUTER = "src/modules/tasks/presenter/router.py"
# TESTING / DEMO ONLY (docs/development/test-doubles.md). Golden frontends: hand-written, convention-correct
# implementations of these FrontendSpec examples only; any other FrontendSpec fails the fake frontend lane.
GOLDEN_FRONTENDS = {
    "Northwind Studio": GOLDEN.parent / "frontend" / "static_landing",  # examples/frontend-specs/static-landing.json
    "Project Tracker": GOLDEN.parent / "frontend" / "project_tracker",  # …/project-tracker-dynamic.json
}
FRONTEND_SHELL = "src/components/layout/SiteShell.tsx"
PLANTED_COLOR = "text-[#b91c1c] "


def golden_frontend_for(workdir: Path) -> Path | None:
    spec_path = workdir / ".bga" / "frontend-spec.json"
    if not spec_path.is_file():
        return None
    import json

    name = (json.loads(spec_path.read_text()).get("project") or {}).get("name")
    return GOLDEN_FRONTENDS.get(name)


def demo_scenario(delay_s: float = 0.3) -> dict[str, list[FakeStep]]:
    """Replays a recorded, convention-correct implementation of `examples/specs/two-entity.json`
    (`golden/two_entity`, one step per planned module) with one deliberate defect: the tasks router is written
    with a syntax error, so validation fails once and the repair loop runs. Any other spec fails validation."""
    fixed_router = (GOLDEN / "tasks" / _TASK_ROUTER).read_text()
    return {
        "generate_database": [FakeStep(sleep_s=delay_s, copy_from=GOLDEN / "database")],
        "generate_backend": [
            FakeStep(sleep_s=delay_s, copy_from=GOLDEN / "projects"),
            FakeStep(
                sleep_s=delay_s,
                copy_from=GOLDEN / "tasks",
                write={_TASK_ROUTER: fixed_router + "\n\ndef broken(:\n"},
            ),
        ],
        "generate_tests": [
            FakeStep(sleep_s=delay_s, copy_from=GOLDEN / "tests_projects"),
            FakeStep(sleep_s=delay_s, copy_from=GOLDEN / "tests_tasks"),
        ],
        "repair_code": [
            FakeStep(
                sleep_s=delay_s,
                write={_TASK_ROUTER: fixed_router},
                message="Fixed the syntax error in the tasks router.",
            )
        ],
        # First call (the shell) writes the whole golden frontend with one defect; the page calls change nothing.
        "generate_frontend": [
            FakeStep(sleep_s=delay_s, golden_frontend=True, plant_frontend_defect=True),
            FakeStep(sleep_s=delay_s, message="The page is already in place."),
        ],
        "repair_frontend": [
            FakeStep(sleep_s=delay_s, golden_frontend=True, message="Replaced the hard-coded colour with a token."),
        ],
        "*": [FakeStep(write={"FAKE_ENGINE.md": "Written by the fake engine.\n"})],
    }


DEMO_SCENARIO = demo_scenario()
DEFAULT_SCENARIO = DEMO_SCENARIO


class FakeEngine(ICodeEngine):
    """TESTING / DEMO ONLY (docs/development/test-doubles.md). Deterministic engine for tests and UI work:
    replays FakeSteps per purpose, never calls a model.

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
        started_at = datetime.now(UTC)
        before = snapshot(workdir)
        tools: list[ToolCall] = []

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
                source = golden_frontend_for(workdir) if step.golden_frontend else step.copy_from
                if source is not None:
                    shutil.copytree(source, workdir, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
                    await emit(EngineEventKind.TOOL_USE, f"Copy {source.name}", tool="Copy")
                    tools.append(ToolCall(name="Copy", target=source.name, started_at=datetime.now(UTC)))
                if source is not None and step.plant_frontend_defect:
                    shell = workdir / FRONTEND_SHELL
                    shell.write_text(shell.read_text().replace('className="', f'className="{PLANTED_COLOR}', 1))
                for relative, content in step.write.items():
                    target = ensure_inside(workdir / relative, workdir)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content)
                    await emit(EngineEventKind.TOOL_USE, f"Write {relative}", tool="Write", target=relative)
                    tools.append(ToolCall(name="Write", target=relative, started_at=datetime.now(UTC)))
                    await emit(EngineEventKind.TOOL_RESULT, "ok: written", isError=False)
                for relative in step.delete:
                    ensure_inside(workdir / relative, workdir).unlink(missing_ok=True)
                    await emit(EngineEventKind.TOOL_USE, f"Delete {relative}", tool="Delete", target=relative)
                    tools.append(ToolCall(name="Delete", target=relative, started_at=datetime.now(UTC)))
                await emit(EngineEventKind.MESSAGE, step.message)
        finally:
            self._cancels.pop(request.invocation_id, None)

        usage = EngineUsage(
            input_tokens=1000,
            output_tokens=200,
            cache_read_tokens=400,
            cost_usd=0.0,
            cost_source="reported",
            model="fake",
        )
        model_calls = _fake_calls(started_at, datetime.now(UTC), tools)
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
            model_calls=model_calls,
        )


def _fake_calls(started: datetime, ended: datetime, tools: list[ToolCall]) -> list[ModelCall]:
    """Two scripted model calls that add up to the reported usage: one issues the tools, one answers."""
    middle = started + (ended - started) / 2
    for tool in tools:
        tool.ended_at = tool.started_at
    common = {"model": "fake", "cost_usd": 0.0, "cost_source": "reported", "latency_source": "measured"}
    return [
        ModelCall(
            seq=1, input_tokens=600, output_tokens=150, started_at=started, ended_at=middle, tools=tools, **common
        ),
        ModelCall(
            seq=2,
            input_tokens=400,
            output_tokens=50,
            cache_read_tokens=400,
            started_at=middle,
            ended_at=ended,
            **common,
        ),
    ]
