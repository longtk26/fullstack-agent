"""Story 17.5: owned files restored and mechanical fixes applied before validation, committed as `node:autofix`."""

import asyncio
import subprocess

import pytest

from src.engines.fake_engine import FakeEngine, FakeStep, demo_scenario
from src.orchestrator.autofix import autofix, fixable_files
from src.orchestrator.frontend_scaffold import changed_owned as frontend_changed_owned
from src.orchestrator.frontend_scaffold import scaffold_frontend
from src.orchestrator.scaffold import changed_owned, record_owned, scaffold_project
from src.orchestrator.workspace import WorkspaceManager
from src.sandbox import ExecResult, ISandbox
from tests.generation_helpers import TEMPLATE
from tests.test_frontend_scaffold import inputs
from workflow_helpers import events, node_runs, run_job, submit


class FixingSandbox(ISandbox):
    """Records commands; a `ruff`/`eslint` command rewrites `fix` (relative path → new content) as the tool would."""

    db_url = test_db_url = ""

    def __init__(self, project, fix=None, shared=None):
        self.project, self.fix, self.shared, self.commands = project, fix or {}, shared, []

    async def start(self):
        pass

    async def stop(self):
        pass

    async def reset_database(self, name):
        pass

    async def shared_dependencies(self):
        return self.shared

    async def exec(self, command, timeout_s=None, env=None, egress=False):
        self.commands.append(command)
        if "ruff" in command or "eslint" in command:
            for relative, content in self.fix.items():
                (self.project / relative).write_text(content)
        return ExecResult(exit_code=0, duration_ms=1, stdout="", stderr="")


def backend(tmp_path):
    manager = WorkspaceManager(tmp_path, max_mb=50)
    workspace = manager.create("gen_autofix")
    scaffold_project(TEMPLATE, workspace.project, "X")
    record_owned(workspace.project)
    manager.commit(workspace, "node:scaffold")
    return manager, workspace


def frontend(tmp_path):
    manager = WorkspaceManager(tmp_path, max_mb=50)
    workspace = manager.create("gen_autofix_fe")
    spec, contract, plan = inputs("static-landing")
    scaffold_frontend(manager.create_frontend(workspace), plan, spec, contract)
    manager.commit(workspace, "node:scaffold_frontend attempt:1", repo="frontend")
    return manager, workspace


def test_owned_backend_files_go_back_to_the_scaffold_version(tmp_path):
    manager, workspace = backend(tmp_path)
    project = workspace.project
    main = (project / "src/main.py").read_text()
    (project / "src/main.py").write_text("app = None\n")
    (project / "docker-entrypoint.sh").unlink()
    (project / "src/libs/extra.py").write_text("x = 1\n")  # added under an owned folder: left to conventions

    result = asyncio.run(autofix(manager, workspace, "project", None))

    assert result.restored == ["docker-entrypoint.sh", "src/main.py"] and result.fixed == []
    assert (project / "src/main.py").read_text() == main
    assert (project / "docker-entrypoint.sh").stat().st_mode & 0o111
    assert changed_owned(project) == ["src/libs/extra.py"]


def test_an_owned_file_the_scaffold_commit_does_not_hold_is_left_alone(tmp_path):
    manager, workspace = backend(tmp_path)
    project = workspace.project
    (project / "src/main.py").write_text("# regenerated after the scaffold\n")
    record_owned(project)  # recorded, but never committed
    (project / "src/main.py").write_text("app = None\n")

    result = asyncio.run(autofix(manager, workspace, "project", None))

    assert result.restored == [] and changed_owned(project) == ["src/main.py"]


def test_owned_frontend_files_go_back_to_the_scaffold_version(tmp_path):
    manager, workspace = frontend(tmp_path)
    site = workspace.frontend / "src/config/site.ts"
    original = site.read_text()
    site.write_text("export const siteConfig = {};\n")

    result = asyncio.run(autofix(manager, workspace, "frontend", None))

    assert result.restored == ["src/config/site.ts"] and site.read_text() == original
    assert frontend_changed_owned(workspace.frontend) == []


def test_ruff_runs_on_the_files_the_engine_may_edit_and_reports_what_changed(tmp_path):
    manager, workspace = backend(tmp_path)
    project = workspace.project
    module = project / "src/modules/tasks/presenter/router.py"
    module.parent.mkdir(parents=True)
    module.write_text("import sys, os\n")
    (project / ".claude").mkdir()
    (project / ".claude/hook.py").write_text("x = 1\n")
    sandbox = FixingSandbox(project, fix={"src/modules/tasks/presenter/router.py": "import os\nimport sys\n"})

    result = asyncio.run(autofix(manager, workspace, "project", sandbox))

    assert result.fixed == ["src/modules/tasks/presenter/router.py"]
    [command] = sandbox.commands
    assert command.startswith("ruff check --fix --exit-zero") and "ruff format" in command
    assert "src/modules/tasks/presenter/router.py" in command
    assert "src/main.py" not in command and ".claude/hook.py" not in command  # owned / tool folders
    assert "src/main.py" not in fixable_files(project, "project")


def test_eslint_uses_the_shared_node_modules_or_installs_first(tmp_path):
    manager, workspace = frontend(tmp_path)
    project = workspace.frontend
    page = project / "src/features/site/components/About.tsx"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text("export function About() {\n  let title = 'About';\n  return <h1>{title}</h1>;\n}\n")
    assert "src/features/site/components/About.tsx" in fixable_files(project, "frontend")
    assert "src/app/about/page.tsx" not in fixable_files(project, "frontend")  # generated route (17.2)
    assert "src/config/site.ts" not in fixable_files(project, "frontend")  # owned
    assert not [name for name in fixable_files(project, "frontend") if not name.startswith("src/")]

    fix = {"src/features/site/components/About.tsx": page.read_text() + "\n"}
    shared = FixingSandbox(project, fix=fix, shared="bga-fe-modules-x")
    assert asyncio.run(autofix(manager, workspace, "frontend", shared)).fixed == [
        "src/features/site/components/About.tsx"
    ]
    assert len(shared.commands) == 1 and shared.commands[0].startswith("pnpm exec eslint --fix")

    own = FixingSandbox(project)
    assert asyncio.run(autofix(manager, workspace, "frontend", own)).fixed == []
    assert own.commands[0] == "pnpm install --frozen-lockfile --offline" and "eslint --fix" in own.commands[1]


@pytest.mark.usefixtures("clean_redis")
def test_an_engine_edit_to_an_owned_file_no_longer_needs_a_repair(client, user_headers, tmp_path):
    scenario = demo_scenario(0)
    step = scenario["generate_tests"][0]
    scenario["generate_tests"][0] = step.model_copy(update={"write": {"src/main.py": "app = None\n"}})
    assert isinstance(step, FakeStep)
    generation_id = submit(client, user_headers)

    assert run_job(tmp_path, generation_id, engine=FakeEngine(tmp_path, scenario)) == "COMPLETED"

    [fix] = [e.payload for e in events(generation_id) if e.type == "validation.autofix"]
    assert fix["restored"] == ["src/main.py"] and fix["fixed"] == [] and fix["attempt"] == 1
    conventions = [e.status for e in events(generation_id) if e.payload.get("check") == "conventions"]
    assert conventions == ["skipped", "passed"]  # attempt 1 stops at the planted syntax error
    # One repair, for the syntax error only: without the restore, src/main.py would fail conventions in attempt 2.
    assert [r.node for r in node_runs(generation_id)].count("repair_code") == 1
    validation = [r for r in node_runs(generation_id) if r.node == "run_validation"]
    assert validation[0].summary["restoredOwned"] == 1
    project = tmp_path / generation_id / "project"
    log = subprocess.run(["git", "log", "--format=%s"], cwd=project, capture_output=True, text=True).stdout
    assert "node:autofix attempt:1" in log
