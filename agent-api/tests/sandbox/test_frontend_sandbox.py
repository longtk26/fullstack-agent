"""Builds and tests a generated frontend for real in the Node sandbox (Story 13.4). Opt in with
BGA_SANDBOX_TESTS=1 (needs Docker and `make runner-node`). Workspaces live under .data/ because Docker Desktop
only shares configured host paths."""

import asyncio
import os
import shutil
import uuid

import pytest

from src.engines.fake_engine import GOLDEN_FRONTENDS
from src.modules.shared.domain.frontend_spec import validate_frontend_spec_text
from src.orchestrator.frontend_planner import plan_frontend
from src.orchestrator.frontend_scaffold import scaffold_frontend
from src.orchestrator.frontend_validation import FrontendValidationRequest, SandboxFrontendValidationRunner
from src.sandbox import DockerSandboxProvider
from tests.generation_helpers import EXAMPLES, REPO

pytestmark = pytest.mark.skipif(os.environ.get("BGA_SANDBOX_TESTS") != "1", reason="sandbox tests are opt-in")


@pytest.fixture
def landing():
    spec = validate_frontend_spec_text((EXAMPLES / "frontend-specs" / "static-landing.json").read_text()).normalized
    plan = plan_frontend(spec)
    project = REPO / ".data" / "test-sandbox" / uuid.uuid4().hex[:10] / "frontend"
    scaffold_frontend(project, plan, spec)
    shutil.copytree(GOLDEN_FRONTENDS["Northwind Studio"], project, dirs_exist_ok=True)
    yield project, plan
    shutil.rmtree(project.parent, ignore_errors=True)


def _validate(project, plan):
    async def go():
        sandbox = DockerSandboxProvider().for_job(f"gen_TESTFE{uuid.uuid4().hex[:8].upper()}", project, "frontend")
        try:
            request = FrontendValidationRequest(project=project, plan=plan, run_tests=True, sandbox=sandbox)
            return await SandboxFrontendValidationRunner().run(request)
        finally:
            await sandbox.stop()

    return asyncio.run(go())


def test_golden_static_site_passes_every_check_offline(landing):
    project, plan = landing
    outcome = _validate(project, plan)
    assert outcome.summary == dict.fromkeys(
        ("install", "typecheck", "lint", "conventions", "build", "routes", "tests"), "passed"
    ), outcome.digest
    assert (project / "out" / "services" / "index.html").is_file()


def test_a_type_error_fails_typecheck_and_skips_build(landing):
    project, plan = landing
    page = project / "src/app/work/page.tsx"
    page.write_text(page.read_text().replace("return <Gallery items={projects} />;", "return <Gallery items={42} />;"))
    outcome = _validate(project, plan)
    assert outcome.summary["typecheck"] == "failed" and outcome.summary["build"] == "skipped"
    typecheck = next(result for result in outcome.results if result.check == "typecheck")
    assert typecheck.details[0]["file"] == "src/app/work/page.tsx"
    assert "src/app/work/page.tsx" in outcome.implicated_files


def test_eslint_autofix_then_every_check_passes_on_the_shared_node_modules():
    """Story 17.5: fixable ESLint findings are fixed before the checks; node_modules comes from the shared, read-only
    volume for this dependency set (no per-project install)."""
    from src.orchestrator.autofix import autofix
    from src.orchestrator.workspace import WorkspaceManager

    spec = validate_frontend_spec_text((EXAMPLES / "frontend-specs" / "static-landing.json").read_text()).normalized
    plan = plan_frontend(spec)
    root = REPO / ".data" / "test-sandbox" / uuid.uuid4().hex[:10]
    manager = WorkspaceManager(root, max_mb=2000)
    workspace = manager.create(f"gen_TESTFEFIX{uuid.uuid4().hex[:6].upper()}")
    project = manager.create_frontend(workspace)
    scaffold_frontend(project, plan, spec)
    shutil.copytree(GOLDEN_FRONTENDS["Northwind Studio"], project, dirs_exist_ok=True)
    manager.commit(workspace, "node:scaffold_frontend attempt:1", repo="frontend")
    helper = project / "src/features/home/format-title.ts"
    helper.parent.mkdir(parents=True, exist_ok=True)
    helper.write_text(
        "export function formatTitle(name: string): string {\n  let title = name.trim();\n  return title;\n}\n"
    )

    async def go():
        sandbox = DockerSandboxProvider().for_job(workspace.root.name, project, "frontend")
        try:
            shared = await sandbox.shared_dependencies()
            fixed = await autofix(manager, workspace, "frontend", sandbox)
            request = FrontendValidationRequest(project=project, plan=plan, run_tests=True, sandbox=sandbox)
            return shared, fixed, await SandboxFrontendValidationRunner().run(request)
        finally:
            await sandbox.stop()

    try:
        shared, fixed, outcome = asyncio.run(go())
        assert shared is not None and shared.startswith("bga-fe-modules-")
        assert fixed.fixed == ["src/features/home/format-title.ts"] and "const title" in helper.read_text()
        assert outcome.summary == dict.fromkeys(
            ("install", "typecheck", "lint", "conventions", "build", "routes", "tests"), "passed"
        ), outcome.digest
        install = next(result for result in outcome.results if result.check == "install")
        assert "shared node_modules" in install.summary
        assert not any((project / "node_modules").iterdir())  # nothing was copied into the workspace
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_dynamic_generation_switches_to_live_and_passes_live_smoke(client, user_headers):
    """Stories 14.1–14.3: parallel backend + frontend sandboxes, live preview switch and live Playwright smoke."""
    import json

    from src.engines.fake_engine import FakeEngine, demo_scenario
    from src.libs.queue import PreviewCommandBus
    from src.libs.redaction import Redactor
    from src.modules.generations.infrastructure.adapters import EventPublisher
    from src.orchestrator.previews import PreviewService
    from src.orchestrator.store import JobStore
    from src.orchestrator.validation import SandboxValidationRunner
    from src.preview.docker_frontend_preview import DockerFrontendPreviewRuntime
    from src.preview.docker_preview import DockerPreviewRuntime
    from tests.workflow_helpers import TWO_ENTITY, generation, redis_client, runner_ctx

    root = REPO / ".data" / "test-sandbox" / uuid.uuid4().hex[:10]
    root.mkdir(parents=True)
    tracker = json.loads((EXAMPLES / "frontend-specs" / "project-tracker-dynamic.json").read_text())
    resp = client.post(
        "/api/v1/generations",
        json={"mode": "dynamic", "frontendSpec": tracker, "backendSpec": TWO_ENTITY, "options": {"engine": "fake"}},
        headers=user_headers,
    )
    assert resp.status_code == 202, resp.text
    generation_id = resp.json()["generationId"]
    backend_rt, frontend_rt = DockerPreviewRuntime(), DockerFrontendPreviewRuntime()
    store = JobStore()

    async def go():
        redis = redis_client()
        try:
            events = EventPublisher(redis, Redactor())
            previews = PreviewService(backend_rt, store, events, PreviewCommandBus(redis), frontend_runtime=frontend_rt)
            async with runner_ctx(
                root,
                engine=FakeEngine(root, demo_scenario(0)),
                validator=SandboxValidationRunner(),
                frontend_validator=SandboxFrontendValidationRunner(),
                sandboxes=DockerSandboxProvider(),
                previews=previews,
                on_completed=previews.request_start,
            ) as runner:
                try:
                    return await runner.run(generation_id)
                finally:
                    for kind in ("frontend", "backend"):
                        await previews.delete(generation_id, kind)
        finally:
            await redis.aclose()

    try:
        status = asyncio.run(go())
        row = generation(generation_id)
        assert status == "COMPLETED", row.error_summary
        assert row.lanes == {"backend": "COMPLETED", "frontend": "COMPLETED", "integration": "COMPLETED"}
    finally:
        if not os.environ.get("BGA_KEEP_SANDBOX_DIRS"):
            shutil.rmtree(root, ignore_errors=True)
