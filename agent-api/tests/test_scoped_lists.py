"""A list scoped by its path (`/projects/{projectId}/tasks`): the path parameter is the filter, never also a query
parameter of the same name (gen_01M6JMBCKWQ8TZ4TMW2FJ6TWJ6: duplicate `fieldId` in the frontend's types)."""

import copy
import json

from generation_helpers import EXAMPLES

from src.modules.shared.domain.backend_spec import validate_spec_text
from src.orchestrator.backend_codegen import module_files, module_tests
from src.orchestrator.contract import build_contract
from src.orchestrator.frontend_codegen import types_ts
from src.orchestrator.planner import build_plan
from src.orchestrator.validation import CheckResult, ValidationOutcome, generator_bug_files

SCOPED = {
    "operationId": "task.listForProject",
    "type": "crud",
    "action": "list",
    "entity": "Task",
    "method": "GET",
    "path": "/projects/{projectId}/tasks",
    "pagination": True,
    "filters": ["projectId", "status"],
    "sort": ["dueDate"],
}


def scoped_spec(op: dict = SCOPED) -> dict:
    spec = copy.deepcopy(json.loads((EXAMPLES / "specs" / "two-entity.json").read_text()))
    spec["operations"].append(copy.deepcopy(op))
    result = validate_spec_text(json.dumps(spec))
    assert result.report.valid, result.report.errors
    return result.normalized


def _planned(spec: dict) -> tuple[dict, dict]:
    plan = build_plan(spec)
    tasks = next(m for m in plan["modules"] if m["entity"] == "Task")
    return plan, next(op for op in tasks["operations"] if op["operationId"] == "task.listForProject")


def test_the_path_parameter_is_a_filter_bound_to_the_path():
    _, op = _planned(scoped_spec())
    assert [(f["param"], f.get("in")) for f in op["filters"]] == [("projectId", "path"), ("status", None)]
    # Also without the spec declaring it a filter: the path scopes the list either way.
    _, op = _planned(scoped_spec({**SCOPED, "filters": ["status"]}))
    assert [(f["param"], f.get("in")) for f in op["filters"]] == [("projectId", "path"), ("status", None)]


def test_contract_and_frontend_types_name_the_parameter_once():
    spec = scoped_spec()
    plan = build_plan(spec)
    contract = build_contract(spec, plan)
    parameters = contract["paths"]["/projects/{projectId}/tasks"]["get"]["parameters"]
    assert [(p["name"], p["in"]) for p in parameters if p["name"] == "projectId"] == [("projectId", "path")]
    types = types_ts(contract)
    block = types[types.index("export type TListForProjectTasksParams") :]
    assert block[: block.index("};")].count("projectId") == 1


def test_router_passes_the_path_value_and_the_tests_call_the_real_url():
    spec = scoped_spec()
    plan = build_plan(spec)
    module = next(m for m in plan["modules"] if m["entity"] == "Task")
    router = module_files(plan, spec, module)["src/modules/tasks/presenter/router.py"]
    handler = router[router.index("async def list_for_project_tasks") :].split("\n\n")[0]
    assert "projectId: uuid.UUID," in handler
    assert 'alias="projectId"' not in handler
    assert "usecase.execute(projectId, status, sort, limit, offset)" in handler
    tests = next(iter(module_tests(plan, spec, module).values()))
    scoped = tests[tests.index("def test_list_for_project_tasks__filter_project_id") :]
    assert "{projectId}" not in tests
    assert 'client.get(f"/projects/{scope_project_id}/tasks")' in scoped
    assert "_seed_task(project_id=scope_project_id)\n    _seed_task()\n" in scoped


def _outcome(*results: CheckResult) -> ValidationOutcome:
    return ValidationOutcome(results=list(results), digest="", implicated_files=[])


def test_frontend_failures_only_in_owned_files_are_a_generator_bug_but_conventions_never_are():
    owned = {"src/lib/api/types.ts"}
    typecheck = CheckResult(check="typecheck", status="failed", details=[{"file": "src/lib/api/types.ts"}])
    conventions = CheckResult(check="conventions", status="failed", details=[{"file": "src/lib/api/types.ts"}])
    assert generator_bug_files(_outcome(typecheck), owned) == ["src/lib/api/types.ts"]
    assert generator_bug_files(_outcome(typecheck, conventions), owned) == [], "the engine changed an owned file"
