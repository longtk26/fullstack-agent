import json
import os
import shutil
import uuid

import docker
import pytest

from src.engines import EngineContext, PromptLibrary
from src.engines.registry import engine_skills
from src.orchestrator.backend.validation import SandboxValidationRunner
from src.sandbox import DockerSandboxProvider
from tests.generation_helpers import EXAMPLES, REPO
from tests.test_scoped_lists import scoped_spec
from tests.workflow_helpers import events, generation, node_runs, run_job, submit

pytestmark = pytest.mark.skipif(os.environ.get("BGA_SANDBOX_TESTS") != "1", reason="sandbox tests are opt-in")


def test_fake_generation_is_validated_for_real_and_repaired(client, user_headers):
    root = REPO / ".data" / "test-sandbox" / uuid.uuid4().hex[:10]
    root.mkdir(parents=True)
    try:
        generation_id = submit(client, user_headers)

        # Same workspace preparation as production: the skill and CLAUDE.md land in the project.
        skills = [skill.path for skill in engine_skills()]
        context = EngineContext(conventions=PromptLibrary().conventions(), skill_dirs=skills)
        status = run_job(
            root,
            generation_id,
            validator=SandboxValidationRunner(),
            sandboxes=DockerSandboxProvider(),
            engine_context=context,
        )

        detail = client.get(f"/api/v1/generations/{generation_id}", headers=user_headers).json()
        assert status == "COMPLETED", generation(generation_id).error_summary
        assert detail["validation"] == {check: "passed" for check in detail["validation"]}
        assert len(detail["validation"]) == 8
        assert [(r.node, r.status) for r in node_runs(generation_id) if r.node == "run_validation"] == [
            ("run_validation", "failed"),
            ("run_validation", "succeeded"),
        ]
        project = root / generation_id / "project"
        assert (project / ".claude" / "skills" / "fastapi-skills" / "SKILL.md").exists()
        assert (project / "alembic" / "versions").glob("*_initial_schema.py")
        assert (root / generation_id / "reports" / "openapi.json").exists()
        leftovers = docker.from_env().containers.list(all=True, filters={"label": f"bga.sandbox={generation_id}"})
        assert leftovers == []
    finally:
        if not os.environ.get("BGA_KEEP_SANDBOX_DIRS"):
            shutil.rmtree(root, ignore_errors=True)


def test_custom_operations_answer_the_smoke_calls(client, user_headers):
    """Story 18.11: templates + the golden flashcards completion (three custom operations) pass in the sandbox, the
    custom operations through one smoke call each instead of engine-written tests."""
    root = REPO / ".data" / "test-sandbox" / uuid.uuid4().hex[:10]
    root.mkdir(parents=True)
    try:
        spec = json.loads((EXAMPLES / "specs" / "flashcards.json").read_text())
        generation_id = submit(client, user_headers, spec=spec, crudFromTemplates=True)
        status = run_job(root, generation_id, validator=SandboxValidationRunner(), sandboxes=DockerSandboxProvider())

        assert status in ("COMPLETED", "COMPLETED_WITH_WARNINGS"), generation(generation_id).error_summary
        tests = [e for e in events(generation_id) if e.type == "validation.check" and e.payload["check"] == "tests"]
        assert tests[-1].status == "passed", tests[-1].payload["summary"]
        assert "3 custom operation(s), " in tests[-1].payload["summary"]
        assert "scenario(s) answer as the contract says" in tests[-1].payload["summary"]
        assert "generate_tests" not in {r.node for r in node_runs(generation_id)}
    finally:
        if not os.environ.get("BGA_KEEP_SANDBOX_DIRS"):
            shutil.rmtree(root, ignore_errors=True)


def test_a_list_scoped_by_its_path_passes_its_template_tests(client, user_headers):
    """gen_01M6JMBCKWQ8TZ4TMW2FJ6TWJ6: `/fields/{fieldId}/reviews` ignored its path and its tests called the URL with
    the braces in it. Templates now scope the list by the path and test it on the real URL."""
    root = REPO / ".data" / "test-sandbox" / uuid.uuid4().hex[:10]
    root.mkdir(parents=True)
    try:
        generation_id = submit(client, user_headers, spec=scoped_spec(), crudFromTemplates=True)
        status = run_job(root, generation_id, validator=SandboxValidationRunner(), sandboxes=DockerSandboxProvider())

        assert status in ("COMPLETED", "COMPLETED_WITH_WARNINGS"), generation(generation_id).error_summary
        tests = [e for e in events(generation_id) if e.type == "validation.check" and e.payload["check"] == "tests"]
        assert tests[-1].status == "passed", tests[-1].payload["summary"]
        assert "repair_code" not in {r.node for r in node_runs(generation_id)}
    finally:
        if not os.environ.get("BGA_KEEP_SANDBOX_DIRS"):
            shutil.rmtree(root, ignore_errors=True)
