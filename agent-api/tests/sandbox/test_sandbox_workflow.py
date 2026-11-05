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


def test_a_backend_with_jwt_auth_passes_its_tests_and_scenarios(client, user_headers, tmp_path):
    """Story 10.2: the auth-jwt plugin's module, the protected task routes, their signed-in template tests and the
    401 / sign-in scenarios, all in the real sandbox."""
    from tests.test_auth_jwt import auth_spec

    root = REPO / ".data" / "test-sandbox" / uuid.uuid4().hex[:10]
    root.mkdir(parents=True)
    try:
        auth_spec(tmp_path)
        spec = json.loads((tmp_path / "auth-spec.json").read_text())
        generation_id = submit(client, user_headers, spec=spec, crudFromTemplates=True)
        status = run_job(root, generation_id, validator=SandboxValidationRunner(), sandboxes=DockerSandboxProvider())

        assert status in ("COMPLETED", "COMPLETED_WITH_WARNINGS"), generation(generation_id).error_summary
        tests = [e for e in events(generation_id) if e.type == "validation.check" and e.payload["check"] == "tests"]
        assert tests[-1].status == "passed", tests[-1].payload["summary"]
        assert "scenario(s) answer as the contract says" in tests[-1].payload["summary"]
        assert "skipped" not in tests[-1].payload["summary"]  # protected operations ran, signed in
    finally:
        if not os.environ.get("BGA_KEEP_SANDBOX_DIRS"):
            shutil.rmtree(root, ignore_errors=True)


def test_a_backend_with_role_and_ownership_policies_passes_its_tests_and_scenarios(client, user_headers, tmp_path):
    """Story 10.3: role and ownership policies (owner from the signed-in user, owner-scoped lists, admins bypass),
    their template tests and the wrong-role / another-user's-record scenarios, all in the real sandbox."""
    from tests.test_policies import policy_spec

    root = REPO / ".data" / "test-sandbox" / uuid.uuid4().hex[:10]
    root.mkdir(parents=True)
    try:
        policy_spec(tmp_path)
        spec = json.loads((tmp_path / "policy-spec.json").read_text())
        generation_id = submit(client, user_headers, spec=spec, crudFromTemplates=True)
        status = run_job(root, generation_id, validator=SandboxValidationRunner(), sandboxes=DockerSandboxProvider())

        assert status in ("COMPLETED", "COMPLETED_WITH_WARNINGS"), generation(generation_id).error_summary
        tests = [e for e in events(generation_id) if e.type == "validation.check" and e.payload["check"] == "tests"]
        assert tests[-1].status == "passed", tests[-1].payload["summary"]
        assert "scenario(s) answer as the contract says" in tests[-1].payload["summary"]
        assert "skipped" not in tests[-1].payload["summary"]
    finally:
        if not os.environ.get("BGA_KEEP_SANDBOX_DIRS"):
            shutil.rmtree(root, ignore_errors=True)


def test_a_backend_with_business_rules_passes_its_tests_and_scenarios(client, user_headers, tmp_path):
    """Story 10.4: transition, immutableAfter and sumEquals rules from templates, their template tests and the
    refused / allowed / locked / mismatch scenarios, all in the real sandbox; the vague custom rule stays unbuilt."""
    from tests.test_rules import rules_spec

    root = REPO / ".data" / "test-sandbox" / uuid.uuid4().hex[:10]
    root.mkdir(parents=True)
    try:
        rules_spec(tmp_path)
        spec = json.loads((tmp_path / "rules-spec.json").read_text())
        generation_id = submit(client, user_headers, spec=spec, crudFromTemplates=True)
        status = run_job(root, generation_id, validator=SandboxValidationRunner(), sandboxes=DockerSandboxProvider())

        assert status in ("COMPLETED", "COMPLETED_WITH_WARNINGS"), generation(generation_id).error_summary
        tests = [e for e in events(generation_id) if e.type == "validation.check" and e.payload["check"] == "tests"]
        assert tests[-1].status == "passed", tests[-1].payload["summary"]
        assert "scenario(s) answer as the contract says" in tests[-1].payload["summary"]
    finally:
        if not os.environ.get("BGA_KEEP_SANDBOX_DIRS"):
            shutil.rmtree(root, ignore_errors=True)


@pytest.mark.parametrize("auth", [False, True], ids=["open", "signed-in"])
def test_a_backend_with_file_fields_passes_its_tests_and_scenarios(client, user_headers, tmp_path, auth):
    """Story 10.5: image and file fields against the shared local store: presign, upload and read in the template
    tests, the upload checks, and the presign / not-uploaded scenarios, all in the real sandbox."""
    from tests.test_storage import storage_spec

    root = REPO / ".data" / "test-sandbox" / uuid.uuid4().hex[:10]
    root.mkdir(parents=True)
    try:
        storage_spec(tmp_path, auth=auth)
        spec = json.loads((tmp_path / "storage-spec.json").read_text())
        generation_id = submit(client, user_headers, spec=spec, crudFromTemplates=True)
        status = run_job(root, generation_id, validator=SandboxValidationRunner(), sandboxes=DockerSandboxProvider())

        assert status in ("COMPLETED", "COMPLETED_WITH_WARNINGS"), generation(generation_id).error_summary
        tests = [e for e in events(generation_id) if e.type == "validation.check" and e.payload["check"] == "tests"]
        assert tests[-1].status == "passed", tests[-1].payload["summary"]
        assert "scenario(s) answer as the contract says" in tests[-1].payload["summary"]
    finally:
        if not os.environ.get("BGA_KEEP_SANDBOX_DIRS"):
            shutil.rmtree(root, ignore_errors=True)


def test_a_backend_with_background_jobs_passes_its_tests_and_scenarios(client, user_headers, tmp_path):
    """Story 10.6: event and cron jobs, the queue and worker template tests (rollback, retry, two workers, one cron
    tick), and the smoke check's `python -m src.worker --once` after the calls that enqueue jobs."""
    from tests.test_jobs import jobs_spec

    root = REPO / ".data" / "test-sandbox" / uuid.uuid4().hex[:10]
    root.mkdir(parents=True)
    try:
        jobs_spec(tmp_path)
        spec = json.loads((tmp_path / "jobs-spec.json").read_text())
        generation_id = submit(client, user_headers, spec=spec, crudFromTemplates=True)
        status = run_job(root, generation_id, validator=SandboxValidationRunner(), sandboxes=DockerSandboxProvider())

        assert status in ("COMPLETED", "COMPLETED_WITH_WARNINGS"), generation(generation_id).error_summary
        tests = [e for e in events(generation_id) if e.type == "validation.check" and e.payload["check"] == "tests"]
        assert tests[-1].status == "passed", tests[-1].payload["summary"]
    finally:
        if not os.environ.get("BGA_KEEP_SANDBOX_DIRS"):
            shutil.rmtree(root, ignore_errors=True)


@pytest.mark.parametrize("account", [False, True], ids=["emails", "with-account-emails"])
def test_a_backend_that_sends_email_passes_its_tests_and_finds_its_email(client, user_headers, tmp_path, account):
    """Story 10.7: an email job per trigger, rendered templates, and the smoke check's email in the shared Mailpit;
    with auth, the password reset and email verification links."""
    from tests.test_email import email_spec

    root = REPO / ".data" / "test-sandbox" / uuid.uuid4().hex[:10]
    root.mkdir(parents=True)
    try:
        email_spec(tmp_path, account=account)
        spec = json.loads((tmp_path / "email-spec.json").read_text())
        generation_id = submit(client, user_headers, spec=spec, crudFromTemplates=True)
        status = run_job(root, generation_id, validator=SandboxValidationRunner(), sandboxes=DockerSandboxProvider())

        assert status in ("COMPLETED", "COMPLETED_WITH_WARNINGS"), generation(generation_id).error_summary
        tests = [e for e in events(generation_id) if e.type == "validation.check" and e.payload["check"] == "tests"]
        assert tests[-1].status == "passed", tests[-1].payload["summary"]
    finally:
        if not os.environ.get("BGA_KEEP_SANDBOX_DIRS"):
            shutil.rmtree(root, ignore_errors=True)


@pytest.mark.parametrize("auth", [True, False], ids=["admin", "open"])
def test_a_backend_with_webhooks_passes_its_tests_and_delivers_a_signed_webhook(client, user_headers, tmp_path, auth):
    """Story 10.8: subscriptions, a signed ping delivered by the worker to a receiver in the sandbox, the incoming
    receiver's signature and idempotency tests, and the SSRF guard's."""
    from tests.test_webhooks import webhooks_spec

    root = REPO / ".data" / "test-sandbox" / uuid.uuid4().hex[:10]
    root.mkdir(parents=True)
    try:
        webhooks_spec(tmp_path, auth=auth)
        spec = json.loads((tmp_path / "webhooks-spec.json").read_text())
        generation_id = submit(client, user_headers, spec=spec, crudFromTemplates=True)
        status = run_job(root, generation_id, validator=SandboxValidationRunner(), sandboxes=DockerSandboxProvider())

        assert status in ("COMPLETED", "COMPLETED_WITH_WARNINGS"), generation(generation_id).error_summary
        tests = [e for e in events(generation_id) if e.type == "validation.check" and e.payload["check"] == "tests"]
        assert tests[-1].status == "passed", tests[-1].payload["summary"]
    finally:
        if not os.environ.get("BGA_KEEP_SANDBOX_DIRS"):
            shutil.rmtree(root, ignore_errors=True)


@pytest.mark.parametrize("variant", ["open", "signed-in-with-transition"])
def test_a_backend_with_payments_passes_its_tests_and_pays_a_seeded_record(client, user_headers, tmp_path, variant):
    """Story 10.9: checkout from the record's amount, the fake page's pay / fail / cancel through the signed webhook
    path, settling by the worker, and the smoke check paying a seeded record."""
    from tests.test_payments import payments_spec

    root = REPO / ".data" / "test-sandbox" / uuid.uuid4().hex[:10]
    root.mkdir(parents=True)
    try:
        signed_in = variant != "open"
        payments_spec(tmp_path, auth=signed_in, transition=signed_in)
        spec = json.loads((tmp_path / "payments-spec.json").read_text())
        generation_id = submit(client, user_headers, spec=spec, crudFromTemplates=True)
        status = run_job(root, generation_id, validator=SandboxValidationRunner(), sandboxes=DockerSandboxProvider())

        assert status in ("COMPLETED", "COMPLETED_WITH_WARNINGS"), generation(generation_id).error_summary
        tests = [e for e in events(generation_id) if e.type == "validation.check" and e.payload["check"] == "tests"]
        assert tests[-1].status == "passed", tests[-1].payload["summary"]
    finally:
        if not os.environ.get("BGA_KEEP_SANDBOX_DIRS"):
            shutil.rmtree(root, ignore_errors=True)


def test_a_backend_with_concurrency_rules_passes_its_concurrent_tests_and_scenarios(client, user_headers, tmp_path):
    """Story 10.10: capacity under a row lock, noOverlap as an exclusion constraint (btree_gist), uniqueTogether as a
    partial unique index; their concurrent template tests and the full / overlap / duplicate scenarios."""
    from tests.test_concurrency_rules import booking_spec

    root = REPO / ".data" / "test-sandbox" / uuid.uuid4().hex[:10]
    root.mkdir(parents=True)
    try:
        booking_spec(tmp_path)
        spec = json.loads((tmp_path / "booking-spec.json").read_text())
        generation_id = submit(client, user_headers, spec=spec, crudFromTemplates=True)
        status = run_job(root, generation_id, validator=SandboxValidationRunner(), sandboxes=DockerSandboxProvider())

        assert status in ("COMPLETED", "COMPLETED_WITH_WARNINGS"), generation(generation_id).error_summary
        tests = [e for e in events(generation_id) if e.type == "validation.check" and e.payload["check"] == "tests"]
        assert tests[-1].status == "passed", tests[-1].payload["summary"]
    finally:
        if not os.environ.get("BGA_KEEP_SANDBOX_DIRS"):
            shutil.rmtree(root, ignore_errors=True)
