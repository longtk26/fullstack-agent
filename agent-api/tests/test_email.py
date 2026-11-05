"""The email plugin (Story 10.7): emails as jobs of their trigger, paths and placeholders through references,
templates escaped in HTML, the account module (password reset, email verification), and the inbox check."""

import json
from pathlib import Path

from src.orchestrator.backend.planner import build_plan
from src.orchestrator.checks.smoke import expects_mail, smoke_calls
from src.orchestrator.integration.contract import build_contract
from src.orchestrator.plugins.app import plugin_files
from tests.generation_helpers import normalized

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


def email_spec(tmp_path: Path, account: bool = False) -> dict:
    """two-entity: projects have an owner's address; a new task emails it, naming the task and its project."""
    raw = json.loads((EXAMPLES / "specs" / "two-entity.json").read_text())
    project = next(entity for entity in raw["entities"] if entity["name"] == "Project")
    project["fields"].append({"name": "ownerEmail", "type": "string", "required": True, "maxLength": 255})
    raw["emails"] = [
        {"name": "taskAdded", "trigger": {"event": "task.created"}, "to": "task.project.ownerEmail",
         "subject": "New task: {{task.title}}",
         "body": "A task was added to {{ task.project.name }}:\n\n{{task.title}} <due {{task.dueDate}}>"},
        {"name": "dailyNote", "trigger": "cron:0 7 * * *", "to": "team@example.com", "subject": "Good morning",
         "body": "Today's tasks are on the board."},
    ]  # fmt: skip
    if account:
        raw["auth"] = {"type": "jwt", "roles": ["member"], "passwordReset": True, "emailVerification": True}
    (tmp_path / "email-spec.json").write_text(json.dumps(raw))
    return normalized(tmp_path / "email-spec.json")


def test_each_email_is_a_job_of_its_trigger_and_loads_what_its_paths_reach(tmp_path):
    plan = build_plan(email_spec(tmp_path))
    assert [p["name"] for p in plan["plugins"]] == ["rate-limit", "jobs", "email"]
    assert [(job["name"], job["trigger"], job["action"]) for job in plan["jobs"]] == [
        ("emailTaskAdded", {"event": "task.created"}, "email"),
        ("emailDailyNote", {"cron": "0 7 * * *"}, "email"),
    ]
    added = plan["emails"][0]
    assert added["to"] == {"path": "task_project.owner_email"}
    assert added["loads"] == [{"alias": "task_project", "from": "task", "attr": "project_id", "model": "ProjectModel",
                               "pkType": "uuid"}]  # fmt: skip
    task_create = next(op for m in plan["modules"] for op in m["operations"] if op["operationId"] == "task.create")
    assert task_create["emits"] == ["task.created"]


def test_templates_escape_values_in_html_and_handlers_send_through_the_job(tmp_path):
    files = plugin_files(build_plan(email_spec(tmp_path)))
    assert files["src/templates/emails/task_added.subject.j2"] == "New task: {{ task.title }}\n"
    html = files["src/templates/emails/task_added.html.j2"]
    assert "{{ task_project.name }}" in html and "&lt;due {{ task.due_date }}&gt;" in html
    handler = files["src/jobs/email_task_added.py"]
    assert '@job("emailTaskAdded", events=("task.created",), max_attempts=5)' in handler
    assert (
        'found = ctx.session.get(ProjectModel, uuid.UUID(str(task.get("project_id")))) if task.get("project_id")'
        in handler
    )
    assert 'to = task_project.get("owner_email")' in handler and "message_id=str(ctx.job_id)" in handler
    assert 'to = "team@example.com"' in files["src/jobs/email_daily_note.py"]
    assert (
        "def test_task_added_renders_with_its_values_escaped_in_html():" in files["tests/modules/email/test_emails.py"]
    )
    for relative, source in files.items():
        if relative.endswith(".py"):
            compile(source, relative, "exec")


def test_account_emails_add_reset_and_verification_links(tmp_path):
    spec = email_spec(tmp_path, account=True)
    plan = build_plan(spec)
    user = next(m for m in plan["models"] if m["entity"] == "User")
    assert "emailVerifiedAt" in {c["apiName"] for c in user["columns"]}
    account = next(m for m in plan["modules"] if m["name"] == "account")
    assert [op["operationId"] for op in account["operations"]] == [
        "account.requestPasswordReset",
        "account.resetPassword",
        "account.requestEmailVerification",
        "account.verifyEmail",
    ]
    files = plugin_files(plan)
    router = files["src/modules/account/presenter/router.py"]
    assert 'jobs.enqueue("email.passwordReset"' in router and 'claims.get("hash") != fingerprint(' in router
    assert (
        "def test_a_password_reset_link_sets_a_new_password_once(client):"
        in files["tests/modules/email/test_emails.py"]
    )
    contract = build_contract(spec, plan)
    assert "/auth/password-reset/confirm" in contract["paths"]
    invalid = contract["paths"]["/auth/password-reset/confirm"]["post"]["x-bga"]["scenarios"][0]
    assert invalid["expect"] == {"status": 400, "code": "INVALID_TOKEN"}


def test_the_smoke_check_looks_for_the_email_after_the_worker(tmp_path):
    spec = email_spec(tmp_path)
    plan = build_plan(spec)
    assert expects_mail(plan)
    calls, _ = smoke_calls(build_contract(spec, plan), plan)
    assert [call.get("kind") for call in calls[-2:]] == ["worker", "mail"]


def test_email_paths_and_placeholders_are_validated(tmp_path):
    from src.modules.shared.domain.backend_spec.validator import validate_spec_data

    raw = json.loads((EXAMPLES / "specs" / "two-entity.json").read_text())
    raw["emails"] = [
        {"name": "a", "trigger": {"event": "task.created"}, "to": "task.project.nope", "subject": "x", "body": "y"},
        {"name": "b", "trigger": {"event": "task.created"}, "to": "a@example.com", "subject": "{{task.nope}}",
         "body": "{{project.name}}"},
        {"name": "c", "trigger": "cron:0 7 * * *", "to": "a@example.com", "subject": "{{task.title}}", "body": "y"},
        {"name": "d", "trigger": {"event": "task.created"}, "to": "currentUser", "subject": "x", "body": "y"},
    ]  # fmt: skip
    paths = {issue.path for issue in validate_spec_data(raw).report.errors}
    assert paths == {"/emails/0/to", "/emails/1/subject", "/emails/1/body", "/emails/2/subject", "/emails/3/to"}
