import json
import os

import pytest

from src.modules.shared.domain.frontend_site.importer import import_frontend_site
from src.orchestrator.planner import build_plan, dump_plan, handler_name, planned_operations
from tests.generation_helpers import EXAMPLES, normalized, two_entity_plan

SNAPSHOTS = EXAMPLES.parent / "agent-api" / "tests" / "fixtures" / "plans"


@pytest.mark.parametrize("name", ["two-entity", "task-management"])
def test_plan_matches_snapshot(name):
    plan = dump_plan(build_plan(normalized(EXAMPLES / "specs" / f"{name}.json")))
    snapshot = SNAPSHOTS / f"{name}.plan.json"
    if os.environ.get("UPDATE_SNAPSHOTS") or not snapshot.exists():
        snapshot.write_text(plan)
    assert plan == snapshot.read_text(), "plan changed: review, then rerun with UPDATE_SNAPSHOTS=1"


def test_plan_is_deterministic():
    spec = normalized(EXAMPLES / "specs" / "two-entity.json")
    assert dump_plan(build_plan(spec)) == dump_plan(build_plan(json.loads(json.dumps(spec))))


@pytest.mark.parametrize(
    ("operation_id", "is_list", "expected"),
    [
        ("task.create", False, "create_task"),
        ("task.list", True, "list_tasks"),
        ("orderItem.get", False, "get_order_item"),
        ("post.listRelated", False, "list_related_post"),
    ],
)
def test_handler_names(operation_id, is_list, expected):
    assert handler_name(operation_id, list_action=is_list) == expected


def test_two_entity_plan_follows_the_skill_naming():
    plan = two_entity_plan()
    tasks = next(m for m in plan["modules"] if m["name"] == "tasks")

    assert tasks["port"]["interface"] == "ITaskRepository" and tasks["port"]["dep"] == "ITaskRepoDep"
    assert {u["dep"] for u in tasks["usecases"]} >= {"CreateTaskUsecaseDep", "ListTasksUsecaseDep"}
    assert {u["class"]: u["transactional"] for u in tasks["usecases"]}["ListTasksUsecase"] is False
    assert tasks["router"]["variable"] == "task_router"
    assert ("GET", "/tasks/{id}", "task.get") in planned_operations(plan)


def test_models_carry_foreign_keys_enums_and_relationships():
    plan = two_entity_plan()
    task = next(m for m in plan["models"] if m["table"] == "tasks")
    project = next(m for m in plan["models"] if m["table"] == "projects")

    assert task["foreignKeys"] == [{"column": "project_id", "references": "projects.id", "onDelete": "CASCADE"}]
    assert task["enums"][0]["dbName"] == "task_status"
    assert [r["attr"] for r in project["relationships"]] == ["tasks"]
    assert [r["attr"] for r in task["relationships"]] == ["project"]


def test_tests_are_planned_per_operation_and_case():
    ids = {t["id"] for t in two_entity_plan()["tests"]}

    assert {"test_create_project__conflict", "test_create_task__bad_reference", "test_list_tasks__filter_status"} <= ids
    assert "test_create_task__conflict" not in ids  # tasks have no unique column


def test_implicit_foreign_key_and_many_to_many_link():
    spec = normalized(EXAMPLES / "specs" / "two-entity.json")
    task = next(e for e in spec["entities"] if e["name"] == "Task")
    task["fields"] = [f for f in task["fields"] if f["name"] != "projectId"]
    spec["entities"].append(
        {"name": "Tag", "table": "tags", "fields": [{"name": "id", "type": "uuid", "primary": True}]}
    )
    spec["relationships"].append({"name": "taskTags", "type": "many-to-many", "from": "Task", "to": "Tag"})

    plan = build_plan(spec)
    task_model = next(m for m in plan["models"] if m["table"] == "tasks")
    link = next(m for m in plan["models"] if m.get("linkFor") == "taskTags")

    assert next(c for c in task_model["columns"] if c["attr"] == "project_id")["implicit"] is True
    assert link["table"] == "tasks_tags" and link["primaryKey"] == ["task_id", "tag_id"]


def test_custom_operations_are_carried_to_unresolved():
    site = json.loads((EXAMPLES / "frontend" / "revue-de-mode.json").read_text())
    spec = import_frontend_site(site).backend_spec
    from src.modules.shared.domain.backend_spec import validate_spec_text

    plan = build_plan(validate_spec_text(json.dumps(spec)).normalized)

    assert [u["ref"] for u in plan["unresolved"]] == ["post.listRelated"]
