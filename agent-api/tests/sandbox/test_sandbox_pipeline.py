"""Runs generated code for real in the Docker sandbox. Opt in with BGA_SANDBOX_TESTS=1 (needs Docker and
`make runner`). Workspaces live under .data/ because Docker Desktop only shares configured host paths."""

import asyncio
import json
import os
import shutil
import uuid
from pathlib import Path

import pytest

from src.orchestrator.planner import build_plan
from src.orchestrator.scaffold import record_owned, scaffold_project
from src.orchestrator.validation import SandboxValidationRunner, ValidationRequest
from src.sandbox import DockerSandboxProvider
from tests.generation_helpers import REPO, TEMPLATE, golden_project, two_entity_plan

pytestmark = pytest.mark.skipif(os.environ.get("BGA_SANDBOX_TESTS") != "1", reason="sandbox tests are opt-in")


@pytest.fixture
def shared_dir():
    root = REPO / ".data" / "test-sandbox" / uuid.uuid4().hex[:10]
    root.mkdir(parents=True)
    yield root
    shutil.rmtree(root, ignore_errors=True)


def _validate(project: Path, plan: dict, run_tests: bool = True, normalize: bool = True):
    async def go():
        sandbox = DockerSandboxProvider().for_job(f"gen_TEST{uuid.uuid4().hex[:8].upper()}", project)
        try:
            if normalize:  # what the scaffold step does to the pinned template
                await sandbox.exec("ruff check --fix -q . ; ruff format -q .")
                record_owned(project)
            return await SandboxValidationRunner().run(ValidationRequest(project, plan, run_tests, sandbox))
        finally:
            await sandbox.stop()

    return asyncio.run(go())


def test_sandbox_is_isolated(shared_dir):
    async def go():
        sandbox = DockerSandboxProvider().for_job("gen_TESTISOLATION", shared_dir)
        try:
            network = await sandbox.exec(
                "python -c \"import urllib.request; urllib.request.urlopen('https://example.com', timeout=5)\""
            )
            socket = await sandbox.exec("test -e /var/run/docker.sock")
            root = await sandbox.exec("touch /etc/bga")
            work = await sandbox.exec("touch /work/ok /tmp/ok && id -u")
            return network, socket, root, work
        finally:
            await sandbox.stop()

    network, socket, root, work = asyncio.run(go())

    assert not network.ok and not socket.ok and not root.ok
    assert work.ok and work.stdout.strip() != "0"


def test_base_project_without_modules_passes_every_check(shared_dir):
    project = shared_dir / "project"
    project.mkdir()
    scaffold_project(TEMPLATE, project, "Empty")
    plan = build_plan({"project": {"name": "Empty"}, "entities": [], "operations": [], "relationships": []})

    outcome = _validate(project, plan)

    assert outcome.summary == {check: "passed" for check in outcome.summary}, outcome.digest


def test_golden_two_entity_project_passes_every_check(shared_dir):
    project = golden_project(shared_dir)

    outcome = _validate(project, two_entity_plan())

    assert outcome.summary == {check: "passed" for check in outcome.summary}, outcome.digest
    migrations = list((project / "alembic/versions").glob("*.py"))
    assert len(migrations) == 1 and "sa.Enum(name='task_status').drop" in migrations[0].read_text()


def test_broken_project_reports_structured_failures(shared_dir):
    project = golden_project(shared_dir)
    _validate(project, two_entity_plan())  # normalize the template once, as the scaffold step does
    router = project / "src/modules/projects/presenter/router.py"
    router.write_text("import os\n" + router.read_text())
    repository = project / "src/modules/tasks/infrastructure/persistence/task_repository.py"
    repository.write_text(
        repository.read_text().replace('FOREIGN_KEY_VIOLATION = "23503"', 'FOREIGN_KEY_VIOLATION = "x"')
    )
    model = project / "src/modules/shared/infrastructure/models/project_model.py"
    model.write_text(model.read_text().replace("unique=True", "unique=False"))

    outcome = _validate(project, two_entity_plan(), normalize=False)

    assert outcome.summary["lint"] == "failed" and outcome.summary["migration"] == "failed"
    assert outcome.summary["tests"] == "skipped"  # depends on migration
    assert "F401" in outcome.digest and "column name should be unique" in outcome.digest
    assert "src/modules/projects/presenter/router.py" in outcome.implicated_files

    model.write_text(model.read_text().replace("unique=False", "unique=True"))
    outcome = _validate(project, two_entity_plan(), normalize=False)

    assert outcome.summary["migration"] == "passed"  # regenerated from the fixed model
    assert outcome.summary["tests"] == "failed"
    assert "test_create_task__bad_reference" in outcome.digest
    assert json.loads(json.dumps(outcome.model_dump(mode="json")))  # report is serializable (as write_report does)


def test_autofix_clears_import_order_and_formatting_before_lint(shared_dir):
    """Story 17.5: the findings of the last real backend run (I001 + format) never reach the repair loop."""
    from src.orchestrator.autofix import autofix
    from src.orchestrator.workspace import WorkspaceManager

    manager = WorkspaceManager(shared_dir, max_mb=500)
    workspace = manager.create(f"gen_TESTFIX{uuid.uuid4().hex[:6].upper()}")
    shutil.copytree(golden_project(shared_dir / "golden"), workspace.project, dirs_exist_ok=True)
    repository = workspace.project / "src/modules/tasks/infrastructure/persistence/task_repository.py"

    async def go():
        sandbox = DockerSandboxProvider().for_job(workspace.root.name, workspace.project)
        try:
            await sandbox.exec("ruff check --fix -q . ; ruff format -q .")  # the scaffold's normalization
            record_owned(workspace.project)
            manager.commit(workspace, "node:scaffold")
            lines = repository.read_text().splitlines(keepends=True)
            repository.write_text(lines[1] + lines[0] + "".join(lines[2:]) + "\n\ndef helper( a,b ):\n    return a+b\n")
            dirty = await SandboxValidationRunner()._lint(ValidationRequest(workspace.project, {}, False, sandbox))
            result = await autofix(manager, workspace, "project", sandbox)
            clean = await SandboxValidationRunner()._lint(ValidationRequest(workspace.project, {}, False, sandbox))
            return dirty, result, clean
        finally:
            await sandbox.stop()

    dirty, result, clean = asyncio.run(go())

    assert dirty.status == "failed" and {d["code"] for d in dirty.details} >= {"format"}
    assert result.fixed == ["src/modules/tasks/infrastructure/persistence/task_repository.py"]
    assert clean.status == "passed", clean.details
    assert "def helper(a, b):" in repository.read_text()
