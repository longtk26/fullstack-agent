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
