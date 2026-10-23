import copy

from src.orchestrator.checks.conventions import check_conventions
from src.orchestrator.checks.parity import compare_openapi, compare_schema, missing_tests
from src.orchestrator.checks.parsers import junit_failures, ruff_failures
from src.orchestrator.migrations import add_enum_drops
from tests.generation_helpers import golden_project, two_entity_plan

# What reflect_schema.py printed for the golden project in the sandbox.
GOLDEN_SCHEMA = {
    "tables": {
        "projects": {
            "columns": [
                {"name": "id", "type": "UUID", "nullable": False},
                {"name": "name", "type": "VARCHAR(120)", "nullable": False},
                {"name": "description", "type": "TEXT", "nullable": True},
                {"name": "created_at", "type": "TIMESTAMP WITH TIME ZONE", "nullable": False},
            ],
            "primaryKey": ["id"],
            "foreignKeys": [],
            "uniques": [["name"]],
            "indexes": [],
        },
        "tasks": {
            "columns": [
                {"name": "id", "type": "UUID", "nullable": False},
                {"name": "project_id", "type": "UUID", "nullable": False},
                {"name": "title", "type": "VARCHAR(200)", "nullable": False},
                {"name": "status", "type": "ENUM(task_status)", "nullable": True},
                {"name": "priority", "type": "INTEGER", "nullable": True},
                {"name": "due_date", "type": "DATE", "nullable": True},
            ],
            "primaryKey": ["id"],
            "foreignKeys": [
                {
                    "columns": ["project_id"],
                    "referredTable": "projects",
                    "referredColumns": ["id"],
                    "onDelete": "CASCADE",
                }
            ],
            "uniques": [],
            "indexes": [{"columns": ["project_id"], "unique": False}],
        },
    },
    "enums": {"task_status": ["TODO", "IN_PROGRESS", "DONE"]},
}


def test_golden_project_meets_the_conventions(tmp_path):
    project = golden_project(tmp_path)

    assert check_conventions(project, two_entity_plan()) == []


def test_convention_violations_are_reported_with_the_skill_rule(tmp_path):
    project = golden_project(tmp_path)
    entity = project / "src/modules/shared/domain/entities/task_entity.py"
    entity.write_text("from sqlmodel import Field\n" + entity.read_text())
    usecase = project / "src/modules/tasks/usecases/create_task_usecase.py"
    usecase.write_text(
        usecase.read_text()
        .replace("    @Transactional\n", "")
        .replace("from fastapi import Depends", "from fastapi import Depends, HTTPException")
    )
    (project / "src/routers.py").write_text(
        "from src.modules.health.presenter import health_router\n\nall_router = [health_router]\n"
    )
    (project / "src/main.py").write_text((project / "src/main.py").read_text() + "\n# edited\n")

    rules = {v["rule"] for v in check_conventions(project, two_entity_plan())}

    assert rules == {"entity_pure", "usecase_transactional", "no_http_exception", "router_registered", "owned_file"}


def test_schema_matches_plan():
    assert compare_schema(two_entity_plan(), GOLDEN_SCHEMA) == []


def test_schema_mismatches_are_listed():
    schema = copy.deepcopy(GOLDEN_SCHEMA)
    tasks = schema["tables"]["tasks"]
    tasks["foreignKeys"][0]["onDelete"] = None
    tasks["columns"][2]["nullable"] = True
    schema["tables"]["projects"]["uniques"] = []
    schema["enums"]["task_status"] = ["TODO", "DONE"]

    messages = [p["message"] for p in compare_schema(two_entity_plan(), schema)]

    assert any("foreign key project_id" in m for m in messages)
    assert "column title should be NOT NULL" in messages
    assert "column name should be unique" in messages
    assert any(m.startswith("enum task_status has") for m in messages)


def test_openapi_parity():
    plan = two_entity_plan()
    paths: dict = {"/health": {"get": {"operationId": "health_check_health_get"}}}
    for module in plan["modules"]:
        for op in module["operations"]:
            paths.setdefault(op["path"], {})[op["method"].lower()] = {"operationId": op["operationId"]}
    assert compare_openapi(plan, {"paths": paths}) == []

    paths["/tasks"]["get"]["operationId"] = "list_tasks_tasks_get"
    paths["/extra"] = {"get": {"operationId": "extra"}}

    messages = {p["message"] for p in compare_openapi(plan, {"paths": paths})}
    assert messages == {
        "missing (operation_id='task.list')",
        "not in the plan (operation_id='list_tasks_tasks_get')",
        "not in the plan (operation_id='extra')",
    }


def test_missing_planned_tests_are_reported(tmp_path):
    project = golden_project(tmp_path)
    assert missing_tests(two_entity_plan(), project) == []

    path = project / "tests/modules/tasks/test_task_api.py"
    path.write_text(path.read_text().replace("def test_list_tasks__filter_status", "def test_status_filter"))

    assert [m["test"] for m in missing_tests(two_entity_plan(), project)] == ["test_list_tasks__filter_status"]


def test_enum_types_are_dropped_on_downgrade():
    migration = (
        "def upgrade() -> None:\n"
        "    op.create_table('tasks', sa.Column('status', sa.Enum('A', 'B', name='task_status')))\n\n\n"
        "def downgrade() -> None:\n    op.drop_table('tasks')\n    # ### end Alembic commands ###\n"
    )

    patched = add_enum_drops(migration)

    assert "    sa.Enum(name='task_status').drop(op.get_bind(), checkfirst=True)\n    # ### end" in patched
    assert add_enum_drops(patched) == patched


def test_ruff_and_junit_output_become_structured_failures():
    ruff = '[{"filename": "/work/src/a.py", "location": {"row": 3}, "code": "F401", "message": "unused"}]'
    junit = (
        '<testsuite><testcase classname="tests.modules.tasks.test_task_api" name="test_get_task__ok">'
        '<failure message="assert 500 == 200">File "/work/src/modules/tasks/usecases/get_task_usecase.py", line 12'
        "</failure></testcase></testsuite>"
    )

    assert ruff_failures(ruff) == [{"file": "src/a.py", "line": 3, "code": "F401", "message": "unused"}]
    failure = junit_failures(junit)[0]
    assert failure["file"] == "src/modules/tasks/usecases/get_task_usecase.py" and failure["line"] == 12
    assert failure["test"] == "test_get_task__ok"
