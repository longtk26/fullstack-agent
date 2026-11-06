"""Epic 21: aggregate operations written from templates (BackendSpec `type: "aggregate"`), and the bindings that
tie a static designed page's Metric / Chart / collection components to a collection."""

import copy
import json

from generation_helpers import EXAMPLES, normalized

from src.modules.shared.domain.backend_spec import validate_spec_data
from src.modules.shared.domain.frontend_spec.tree_bindings import bind_tree
from src.orchestrator.backend.codegen import codegen_gaps, module_files, module_tests
from src.orchestrator.backend.planner import build_plan
from src.orchestrator.frontend.codegen import mock_operations
from src.orchestrator.integration.contract import build_contract, contract_operations

TWO_ENTITY = json.loads((EXAMPLES / "specs" / "two-entity.json").read_text())


def with_aggregates(tmp_path) -> dict:
    spec = copy.deepcopy(TWO_ENTITY)
    spec["operations"] += [
        {
            "operationId": "task.count",
            "type": "aggregate",
            "entity": "Task",
            "method": "GET",
            "path": "/tasks/aggregate/count",
            "aggregate": {"fn": "count", "period": "month"},
        },
        {
            "operationId": "task.sumPriorityByStatus",
            "type": "aggregate",
            "entity": "Task",
            "method": "GET",
            "path": "/tasks/aggregate/sumPriorityByStatus",
            "aggregate": {"fn": "sum", "field": "priority", "groupBy": "status", "filters": {"status": "TODO"}},
        },
    ]
    (tmp_path / "spec.json").write_text(json.dumps(spec))
    return normalized(tmp_path / "spec.json")


def test_aggregates_validate_against_their_entity(tmp_path):
    spec = with_aggregates(tmp_path)
    assert [op["type"] for op in spec["operations"][-2:]] == ["aggregate", "aggregate"]
    broken = copy.deepcopy(TWO_ENTITY)
    broken["operations"].append(
        {
            "operationId": "task.avgTitle",
            "type": "aggregate",
            "entity": "Task",
            "method": "POST",
            "path": "/tasks/aggregate/avgTitle",
            "aggregate": {"fn": "avg", "field": "title", "groupBy": "nope"},
        }
    )
    report = validate_spec_data(broken).report
    messages = [issue.message for issue in report.errors]
    assert any("needs a numeric field" in m for m in messages) and any("no field 'nope'" in m for m in messages)
    assert any("are GET" in m for m in messages)


def test_aggregates_are_templated_like_crud(tmp_path):
    spec = with_aggregates(tmp_path)
    plan = build_plan(spec)
    tasks = next(m for m in plan["modules"] if m["entity"] == "Task")
    aggregates = [op for op in tasks["operations"] if op["type"] == "aggregate"]
    assert [op["handler"] for op in aggregates] == ["count_task", "sum_priority_by_status_task"]
    assert aggregates[0]["aggregate"]["dateAttr"] == "due_date", "the period falls back to the entity's date field"
    assert aggregates[1]["aggregate"] == {
        "fn": "sum",
        "field": "priority",
        "attr": "priority",
        "groupBy": "status",
        "groupAttr": "status",
        "period": None,
        "dateAttr": "due_date",
        "filters": {"status": "TODO"},
    }
    assert codegen_gaps(tasks) == [], "no engine call for aggregates"
    assert {"count_task", "sum_priority_by_status_task"} <= set(tasks["port"]["methods"])

    files = module_files(plan, spec, tasks) | module_tests(plan, spec, tasks)
    for relative, text in files.items():
        compile(text, relative, "exec")
    repository = files["src/modules/tasks/infrastructure/persistence/task_repository.py"]
    assert "def count_task(self) -> float:" in repository and "func.count()" in repository
    assert "now.replace(day=1" in repository and "col(TaskModel.due_date) >= " in repository
    assert "select(col(TaskModel.status), func.coalesce(func.sum(col(TaskModel.priority)), 0))" in repository
    assert ".group_by(col(TaskModel.status))" in repository and 'col(TaskModel.status) == "TODO"' in repository
    router = files["src/modules/tasks/presenter/router.py"]
    assert router.index('operation_id="task.count"') < router.index('operation_id="task.get"'), "before /{id}"
    assert "response_model=list[SumPriorityByStatusTaskResponseDto]" in router
    assert "class CountTaskResponseDto(BaseModel):" in files["src/modules/tasks/presenter/dtos/count_task_dto.py"]
    tests = files[tasks["testFile"]]
    assert "def test_count_task__ok(client):" in tests and 'client.get("/tasks/aggregate/count")' in tests
    assert 'all({"key", "value"} <= set(row) for row in body)' in tests


def test_the_contract_and_the_mock_describe_aggregates(tmp_path):
    spec = with_aggregates(tmp_path)
    contract = build_contract(spec)
    ops = contract_operations(contract)
    scalar = ops["task.count"]["operation"]
    grouped = ops["task.sumPriorityByStatus"]["operation"]
    assert scalar["x-bga"]["action"] == "aggregate" and scalar["x-bga"]["mock"] == "aggregate"
    assert scalar["responses"]["200"]["content"]["application/json"]["schema"]["properties"]["value"] == {
        "type": "number"
    }
    items = grouped["responses"]["200"]["content"]["application/json"]["schema"]["items"]
    assert set(items["properties"]) == {"key", "value"} and grouped["x-bga"]["aggregate"]["groupBy"] == "status"
    mocks = {m["operationId"]: m for m in mock_operations(contract)}
    assert mocks["task.count"]["mock"] == "aggregate" and mocks["task.count"]["aggregate"]["fn"] == "count"
    assert mocks["task.sumPriorityByStatus"]["aggregate"]["groupBy"] == "status"
    assert mocks["task.count"]["envelope"] is False or mocks["task.count"]["envelope"] is True  # a value, not a page


# -- bindings ------------------------------------------------------------------------------------------------------


TREE = {
    "type": "main",
    "children": [
        {"type": "Metric", "props": {"collection": "tasks", "fn": "count", "period": "month"}},
        {"type": "Chart", "props": {"collection": "tasks", "fn": "sum", "field": "priority", "groupBy": "status"}},
        {"type": "Metric", "props": {"collection": "tasks", "fn": "avg", "field": "priority"}},
        {
            "type": "CollectionBrowser",
            "props": {"collection": "tasks", "pageSize": 10, "sortFields": ["priority"], "searchFields": ["title"]},
            "children": [
                {
                    "type": "ItemList",
                    "children": [
                        {"type": "RecordField", "props": {"field": "title"}},
                        {"type": "RecordLink", "props": {"detailSlug": "page:task"}},
                    ],
                },
                {"type": "RecordAction", "props": {"action": "delete"}},
            ],
        },
        {
            "type": "CollectionDetail",
            "props": {"collection": "projects"},
            "children": [{"type": "RecordForm", "props": {"mode": "edit"}}],
        },
    ],
}


def test_static_trees_bind_to_collections():
    tree = copy.deepcopy(TREE)
    notes = bind_tree(tree, ["tasks", "projects"], {"task": "/tasks/[id]"})
    assert notes == [] and tree["children"][0]["binding"] == {"collection": "tasks"}
    assert tree["children"][3]["children"][0]["children"][1]["binding"] == {
        "collection": "tasks",
        "route": "/tasks/[id]",
    }
