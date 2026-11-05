"""The rules plugin (Story 10.4): transition, immutableAfter and sumEquals from templates (catalog, use-case checks,
allowedActions, tests, scenarios); custom rules with a planned code for the engine; ambiguous ones not implemented;
ownerOnly through the policies plugin."""

import json
from pathlib import Path

from src.orchestrator.backend.codegen import codegen_gaps, module_files, module_tests
from src.orchestrator.backend.planner import build_plan
from src.orchestrator.checks.smoke import judge, scenario_calls
from src.orchestrator.integration.contract import build_contract, contract_operations
from src.orchestrator.plugins import REGISTRY, extended_spec
from tests.generation_helpers import normalized

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
VAGUE = "Be fair"


def rules_spec(tmp_path: Path, custom: bool = False) -> dict:
    """two-entity, no auth: tasks move TODO → IN_PROGRESS → DONE (or back to TODO) and are final once DONE; a
    project's `totalPoints` is the sum of its tasks' `points`; one vague custom rule (not implemented)."""
    raw = json.loads((EXAMPLES / "specs" / "two-entity.json").read_text())
    project = next(entity for entity in raw["entities"] if entity["name"] == "Project")
    project["fields"].append({"name": "totalPoints", "type": "integer", "required": False, "nullable": True})
    task = next(entity for entity in raw["entities"] if entity["name"] == "Task")
    task["fields"].append({"name": "points", "type": "integer", "required": False, "default": 1})
    raw["rules"] = [
        {"id": "taskStatusFlow", "kind": "transition", "entity": "Task",
         "params": {"field": "status", "transitions": {"TODO": ["IN_PROGRESS"], "IN_PROGRESS": ["DONE", "TODO"]}}},
        {"id": "doneIsFinal", "kind": "immutableAfter", "entity": "Task",
         "params": {"field": "status", "states": ["DONE"]}},
        {"id": "projectPoints", "kind": "sumEquals", "entity": "Project",
         "params": {"field": "totalPoints", "items": "Task", "itemField": "points"}},
        {"id": "fairness", "kind": "custom", "entity": "Project", "description": VAGUE},
    ]  # fmt: skip
    if custom:
        raw["rules"].append(
            {"id": "oneOpenProjectPerName", "kind": "custom", "entity": "Project",
             "description": "A project cannot be created while another project with the same name exists",
             "params": {"field": "name", "status": 409}}
        )  # fmt: skip
    for op in raw["operations"]:
        if op["operationId"] == "task.update":
            op["rules"] = ["taskStatusFlow", "doneIsFinal"]
        elif op["operationId"] == "task.delete":
            op["rules"] = ["doneIsFinal"]
        elif op["operationId"] == "project.update":
            op["rules"] = ["projectPoints", "fairness"]
        elif op["operationId"] == "project.create" and custom:
            op["rules"] = ["oneOpenProjectPerName"]
    (tmp_path / "rules-spec.json").write_text(json.dumps(raw))
    return normalized(tmp_path / "rules-spec.json")


def _module(plan: dict, name: str) -> dict:
    return next(module for module in plan["modules"] if module["name"] == name)


def _files(spec: dict, plan: dict, name: str) -> dict[str, str]:
    module = _module(plan, name)
    return module_files(plan, extended_spec(spec), module) | module_tests(plan, extended_spec(spec), module)


def test_the_predefined_kinds_are_planned_from_templates(tmp_path):
    plan = build_plan(rules_spec(tmp_path))
    tasks, projects = _module(plan, "tasks"), _module(plan, "projects")
    assert {"name": "rules", "version": "1"} in plan["plugins"]
    assert codegen_gaps(tasks) == [] and codegen_gaps(projects) == []  # the vague custom rule is not the engine's
    assert plan["unresolved"] == [
        {
            "kind": "rules",
            "ref": "fairness",
            "message": "Not implemented: its description is too short to say who may do what, in which state",
        }
    ]
    update = next(op for op in tasks["operations"] if op["action"] == "update")
    assert [check["constant"] for check in update["ruleChecks"]] == ["DONE_IS_FINAL", "TASK_STATUS_FLOW"]
    assert {"status": 409, "exception": "ConflictException", "code": "INVALID_TRANSITION"} in update["errors"]
    assert tasks["recordActions"] == [
        "update",
        "delete",
        "transition:TODO",
        "transition:IN_PROGRESS",
        "transition:DONE",
    ]


def test_the_rules_are_a_catalog_checked_in_the_use_cases(tmp_path):
    spec = rules_spec(tmp_path)
    plan = build_plan(spec)
    catalog = REGISTRY["rules"].files(plan)["src/libs/rules/catalog.py"]
    assert 'TASK_STATUS_FLOW = Transition(\n    rule="taskStatusFlow",\n    field="status",\n' in catalog
    assert '        "IN_PROGRESS": ("DONE", "TODO"),\n        "DONE": (),\n' in catalog
    assert (
        'DONE_IS_FINAL = ImmutableAfter(\n    rule="doneIsFinal",\n    field="status",\n    states=("DONE",),'
        in catalog
    )
    tasks = _files(spec, plan, "tasks")
    update = tasks["src/modules/tasks/usecases/update_task_usecase.py"]
    assert update.index("DONE_IS_FINAL.check(current.status)") < update.index(
        "TASK_STATUS_FLOW.check(current.status, dto.status)"
    )
    assert "DONE_IS_FINAL.check(existing.status)" in tasks["src/modules/tasks/usecases/delete_task_usecase.py"]
    projects = _files(spec, plan, "projects")
    usecase = projects["src/modules/projects/usecases/update_project_usecase.py"]
    assert "PROJECT_POINTS.check(dto.total_points, self.project_repo.tasks_total(project_id))" in usecase
    repository = projects["src/modules/projects/infrastructure/persistence/project_repository.py"]
    assert "query = select(func.coalesce(total, 0)).where(col(TaskModel.project_id) == project_id)" in repository
    assert (
        "def tasks_total(self, project_id: uuid.UUID) -> Decimal:"
        in projects["src/modules/projects/ports/output/project_repository.py"]
    )
    for relative, source in {**tasks, **projects, "catalog.py": catalog}.items():
        compile(source, relative, "exec")


def test_allowed_actions_follow_the_records_state(tmp_path):
    spec = rules_spec(tmp_path)
    plan = build_plan(spec)
    dto = _files(spec, plan, "tasks")["src/modules/tasks/presenter/dtos/task_response_dto.py"]
    assert "def allowed_actions(entity: TaskEntity) -> list[str]:" in dto  # no auth: the state alone decides
    assert '"update": not DONE_IS_FINAL.locked(entity.status),' in dto
    assert '"TODO" in TASK_STATUS_FLOW.next_states(entity.status)\n            and not DONE_IS_FINAL.locked' in dto
    assert '"allowed_actions": allowed_actions(entity),' in dto


def test_each_rule_has_template_tests_named_after_it(tmp_path):
    spec = rules_spec(tmp_path)
    plan = build_plan(spec)
    tasks = _files(spec, plan, "tasks")["tests/modules/tasks/test_task_api.py"]
    for name in (
        "test_update_task__task_status_flow_allowed",
        "test_update_task__task_status_flow_refused",
        "test_update_task__done_is_final_locked",
        "test_delete_task__done_is_final_locked",
    ):
        assert f"def {name}(client):" in tasks
    assert "record = _seed_task(status=TaskStatus.TODO)" in tasks
    projects = _files(spec, plan, "projects")["tests/modules/projects/test_project_api.py"]
    assert "_seed_task(project_id=record.id, points=10)" in projects
    assert 'json={"totalPoints": 16})' in projects and "TOTAL_MISMATCH" in projects


def test_the_contract_lists_the_rules_their_errors_and_scenarios(tmp_path):
    spec = rules_spec(tmp_path)
    contract = build_contract(spec)
    ops = {op_id: found["operation"] for op_id, found in contract_operations(contract).items()}
    errors = ops["task.update"]["x-bga"]["errors"]
    assert {"status": 409, "code": "INVALID_TRANSITION", "fields": ["status"], "rule": "taskStatusFlow",
            "message": "status cannot move to that state from the current one"} in errors  # fmt: skip
    names = [scenario["name"] for scenario in ops["task.update"]["x-bga"]["scenarios"]]
    assert names[-3:] == [
        "locked record",
        "refused transition (TODO → DONE)",
        "allowed transition (TODO → IN_PROGRESS)",
    ]
    assert [s["name"] for s in ops["task.delete"]["x-bga"]["scenarios"]] == ["unknown id", "locked record"]
    mismatch = ops["project.update"]["x-bga"]["scenarios"][-1]
    assert mismatch["name"] == "total mismatch" and mismatch["expect"] == {"status": 422, "code": "TOTAL_MISMATCH"}
    assert "Not implemented: rule fairness is ambiguous" in ops["project.update"]["description"]
    rules = {rule["id"]: rule for rule in contract["x-bga"]["rules"]}
    assert rules["doneIsFinal"]["operations"] == ["task.delete", "task.update"]
    assert rules["doneIsFinal"]["implementation"] == "template" and rules["fairness"]["implementation"] == "none"
    assert contract["x-bga"]["entities"]["Task"]["allowedActions"][2:] == [
        "transition:TODO",
        "transition:IN_PROGRESS",
        "transition:DONE",
    ]


def test_a_custom_rule_gets_a_code_the_engine_raises_and_a_scenario_that_allows_it(tmp_path):
    spec = rules_spec(tmp_path, custom=True)
    plan = build_plan(spec)
    projects = _module(plan, "projects")
    create = next(op for op in projects["operations"] if op["action"] == "create")
    assert create["customRules"] == [
        {
            "id": "oneOpenProjectPerName",
            "code": "ONE_OPEN_PROJECT_PER_NAME",
            "status": 409,
            "message": "A project cannot be created while another project with the same name exists",
            "field": "name",
        }
    ]
    assert codegen_gaps(projects) == ["project.create: business rules"]
    note = REGISTRY["rules"].engine_note(plan)
    assert (
        '`oneOpenProjectPerName`: answer 409 with code `ONE_OPEN_PROJECT_PER_NAME` and `details={"fields": ["name"]}`'
        in note
    )
    contract = build_contract(spec, plan)
    calls, _ = scenario_calls(contract)
    success = next(c for c in calls if c["operationId"] == "project.create" and c["scenario"] == "success")
    assert success["expect"]["or"] == [{"status": 409, "code": "ONE_OPEN_PROJECT_PER_NAME"}]
    refused = {"status": 409, "body": '{"error": {"code": "ONE_OPEN_PROJECT_PER_NAME", "message": "taken"}}'}
    assert judge(contract, [success], [refused]) == []
    other = {"status": 409, "body": '{"error": {"code": "CONFLICT", "message": "taken"}}'}
    assert judge(contract, [success], [other]) != []


def test_owner_only_rules_are_ownership(tmp_path):
    from tests.test_auth_jwt import auth_spec

    auth_spec(tmp_path)
    raw = json.loads((tmp_path / "auth-spec.json").read_text())
    next(e for e in raw["entities"] if e["name"] == "Task")["fields"].append(
        {"name": "ownerId", "type": "uuid", "required": True}
    )
    raw["rules"] = [{"id": "ownTasksOnly", "kind": "ownerOnly", "entity": "Task", "params": {"ownerField": "ownerId"}}]
    next(op for op in raw["operations"] if op["operationId"] == "task.update")["rules"] = ["ownTasksOnly"]
    (tmp_path / "owner-only.json").write_text(json.dumps(raw))
    plan = build_plan(normalized(tmp_path / "owner-only.json"))
    tasks = _module(plan, "tasks")
    update = next(op for op in tasks["operations"] if op["action"] == "update")
    assert update["auth"]["ownership"]["field"] == "ownerId" and update["templatedRules"] == ["ownTasksOnly"]
    assert codegen_gaps(tasks) == [] and "rules" not in {p["name"] for p in plan["plugins"]}


def test_a_sum_rule_needs_items_that_reference_the_record(tmp_path):
    from src.modules.shared.domain.backend_spec.validator import validate_spec_data

    raw = json.loads((EXAMPLES / "specs" / "two-entity.json").read_text())
    raw["rules"] = [{"id": "bad", "kind": "sumEquals", "entity": "Task",
                     "params": {"field": "priority", "items": "Project", "itemField": "name"}}]  # fmt: skip
    codes = {(issue.code, issue.path) for issue in validate_spec_data(raw).report.errors}
    assert ("RULE_PARAMS_INVALID", "/rules/0/params/items") in codes
    assert ("RULE_PARAMS_INVALID", "/rules/0/params/itemField") in codes


def test_the_route_of_an_ambiguous_rule_says_it_is_not_implemented(tmp_path):
    spec = rules_spec(tmp_path)
    plan = build_plan(spec)
    router = _files(spec, plan, "projects")["src/modules/projects/presenter/router.py"]
    assert 'description="Not implemented: rule fairness is ambiguous (its description is too short' in router
