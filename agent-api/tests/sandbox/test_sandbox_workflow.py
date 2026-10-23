import os
import shutil
import uuid

import docker
import pytest

from src.engines import EngineContext, PromptLibrary
from src.engines.registry import engine_skills
from src.orchestrator.validation import SandboxValidationRunner
from src.sandbox import DockerSandboxProvider
from tests.generation_helpers import REPO
from tests.workflow_helpers import generation, node_runs, run_job, submit

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
