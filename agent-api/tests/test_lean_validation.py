"""Story 18.11: smoke calls for custom operations, warnings that never block, and the generator-bug stop."""

import json

from test_backend_codegen import with_custom_operation

from src.modules.shared.domain.backend_spec import validate_spec_text
from src.orchestrator.backend.planner import build_plan
from src.orchestrator.backend.validation import (
    CheckResult,
    ValidationOutcome,
    build_digest,
    conventions_check,
    generator_bug_files,
)
from src.orchestrator.checks.smoke import custom_operations, judge, rule_answer, sample_value, smoke_calls
from src.orchestrator.integration.contract import build_contract, presented_record


def _custom(contract, plan):
    """The calls of the custom operations only (since Story 10.0b, the contract's scenarios run first)."""
    calls, skipped = smoke_calls(contract, plan)
    return [call for call in calls if "expect" not in call], skipped


def _pair() -> tuple[dict, dict]:
    result = validate_spec_text(json.dumps(with_custom_operation()))
    assert result.report.valid, result.report.errors
    plan = build_plan(result.normalized)
    return build_contract(result.normalized, plan), plan


def test_one_smoke_call_per_custom_operation_with_its_path_from_the_fixtures():
    contract, plan = _pair()
    assert [op["operationId"] for op in custom_operations(plan)] == ["task.complete"]
    calls, skipped = _custom(contract, plan)
    task = contract["x-bga"]["fixtures"]["Task"][0]
    assert calls == [{"operationId": "task.complete", "method": "POST", "path": f"/tasks/{task['id']}/complete",
                      "body": None}]  # fmt: skip
    assert skipped == []


def test_the_answers_must_have_the_planned_status_and_the_contract_shape():
    contract, plan = _pair()
    calls, _ = _custom(contract, plan)
    task = presented_record(contract, "Task", contract["x-bga"]["fixtures"]["Task"][0])
    status = int(
        next(code for code in contract["paths"]["/tasks/{id}/complete"]["post"]["responses"] if code[0] == "2")
    )
    assert judge(contract, calls, [{"status": status, "body": json.dumps(task)}]) == []

    [wrong] = judge(contract, calls, [{"status": 500, "body": "Internal Server Error"}])
    assert wrong["operation"] == "task.complete" and "got 500" in wrong["message"]
    assert wrong["request"].startswith("POST /tasks/") and wrong["response"] == "Internal Server Error"

    shape = judge(contract, calls, [{"status": status, "body": json.dumps({**task, "id": 7})}])
    assert shape and all(p["operation"] == "task.complete" and "request" in p for p in shape)


def test_a_business_rule_answering_the_guessed_request_is_not_a_failure():
    """gen_01M6JQ7F280RY8FJY21JJZDDDS: `booking.create` answered 409 (the seeded slot was booked) and
    `booking.cancel` 404; the app was right both times."""
    contract, plan = _pair()
    calls, _ = _custom(contract, plan)
    conflict = {"status": 409, "body": json.dumps({"error": {"code": "CONFLICT", "message": "taken"}})}
    assert rule_answer(conflict) and judge(contract, calls, [conflict]) == []
    for answer in (
        {"status": 422, "body": json.dumps({"error": {"code": "VALIDATION_ERROR", "message": "x"}})},
        {"status": 404, "body": "Not Found"},  # no envelope: a route that is not there
    ):
        assert not rule_answer(answer) and judge(contract, calls, [answer])


def test_smoke_bodies_take_seeded_ids_and_a_create_takes_fresh_references():
    contract, plan = _pair()
    fixtures = contract["x-bga"]["fixtures"]
    project, task = fixtures["Project"][0], fixtures["Task"][0]
    contract["components"]["schemas"]["Ref"] = {
        "type": "object",
        "required": ["taskId", "projectId"],
        "properties": {"taskId": {"type": "string"}, "projectId": {"type": "string"}},
    }
    body = {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/Ref"}}}}
    contract["paths"]["/tasks/{id}/complete"]["post"]["requestBody"] = body
    [call], _ = _custom(contract, plan)
    assert call["body"] == {"taskId": task["id"], "projectId": task["projectId"]}, "the operation's own record first"
    contract["paths"]["/tasks/bulk"] = {"post": contract["paths"].pop("/tasks/{id}/complete")["post"]}
    [call], _ = _custom(contract, plan)
    assert call["path"] == "/tasks/bulk"
    assert call["body"]["projectId"] == project["id"], "a create gets the first seeded project, not the task's"


def test_request_bodies_take_the_fixture_fields_and_fill_the_rest():
    contract = {"components": {"schemas": {}}}
    schema = {
        "type": "object",
        "required": ["title", "due", "count", "state"],
        "properties": {
            "title": {"type": "string"},
            "due": {"type": "string", "format": "date"},
            "count": {"type": "integer", "minimum": 3},
            "state": {"enum": ["open", "done"]},
            "note": {"type": ["string", "null"]},
        },
    }
    assert sample_value(contract, schema, {"title": "From the fixture", "note": "kept", "id": "x"}) == {
        "title": "From the fixture",
        "due": "2026-01-15",
        "count": 3,
        "state": "open",
        "note": "kept",
    }


def test_conventions_findings_are_a_warning_that_neither_blocks_nor_reaches_the_digest(tmp_path):
    _, plan = _pair()
    result = conventions_check(tmp_path, plan)  # an empty project: every planned file is missing
    assert result.status == "warning" and result.details
    warning = CheckResult(check="lint", status="warning", summary="2 ruff finding(s)", details=[{"file": "a.py"}])
    outcome = ValidationOutcome(results=[warning, result], digest=build_digest([warning, result]), implicated_files=[])
    assert outcome.failed_checks == [] and "lint" in outcome.warnings and outcome.digest == ""


def _outcome(*results: CheckResult) -> ValidationOutcome:
    return ValidationOutcome(results=list(results), digest="", implicated_files=[])


def test_failures_only_in_generator_owned_files_are_agenerator_bug_files():
    owned = {"src/routers.py", "src/modules/tasks/presenter/router.py", "tests/modules/tasks/test_task_api.py"}
    syntax = CheckResult(check="syntax", status="failed", details=[{"file": "src/routers.py", "line": 3}])
    assert generator_bug_files(_outcome(syntax), owned) == ["src/routers.py"]

    mixed = CheckResult(check="syntax", status="failed", details=[{"file": "src/routers.py"}, {"file": "src/x.py"}])
    assert generator_bug_files(_outcome(mixed), owned) == []
    crash = CheckResult(check="startup", status="failed", details=[])  # no file: could be anywhere
    assert generator_bug_files(_outcome(syntax, crash), owned) == []
    test = CheckResult(check="tests", status="failed", details=[{"file": "tests/modules/tasks/test_task_api.py"}])
    assert generator_bug_files(_outcome(test), owned) == [], "a failing test names its file whatever broke"
    lint = CheckResult(check="lint", status="warning", details=[{"file": "src/routers.py"}])
    assert generator_bug_files(_outcome(lint), owned) == [], "warnings are not failures"
