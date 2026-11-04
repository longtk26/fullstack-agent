"""Story 17.6: the CRUD parts of a backend (models, modules, tests) written from templates, without the engine."""

import copy
import json
import os
from pathlib import Path

import pytest
from generation_helpers import EXAMPLES, normalized
from sqlmodel import SQLModel

from src.engines.fake_engine import FakeEngine, demo_scenario
from src.modules.shared.domain.backend_spec import validate_spec_text
from src.orchestrator.backend_codegen import (
    codegen_gaps,
    database_files,
    database_gaps,
    module_files,
    module_tests,
    routers_file,
)
from src.orchestrator.planner import build_plan
from src.orchestrator.scaffold import add_owned, changed_owned
from workflow_helpers import cli_invocations, events, generation, node_runs, run_job, submit

SNAPSHOTS = Path(__file__).parent / "fixtures" / "backend-codegen"
TWO_ENTITY = json.loads((EXAMPLES / "specs" / "two-entity.json").read_text())
ENGINE_STEPS = ("generate_database", "generate_backend", "complete_backend", "generate_tests")  # none writes tests


def generated(spec: dict) -> dict[str, str]:
    plan = build_plan(spec)
    files = database_files(plan) | {"src/routers.py": routers_file(plan)}
    for module in plan["modules"]:
        files |= module_files(plan, spec, module) | module_tests(plan, spec, module)
    return files


def with_custom_operation() -> dict:
    spec = copy.deepcopy(TWO_ENTITY)
    spec["operations"].append(
        {
            "operationId": "task.complete",
            "type": "custom",
            "entity": "Task",
            "method": "POST",
            "path": "/tasks/{id}/complete",
            "response": {"entity": "Task"},
        }
    )
    return spec


@pytest.mark.parametrize("name", ["two-entity", "shop", "task-management"])
def test_output_is_byte_identical_between_runs_and_matches_the_snapshot(name):
    spec = normalized(EXAMPLES / "specs" / f"{name}.json")
    files = generated(spec)
    assert files == generated(spec)
    snapshot = SNAPSHOTS / f"{name}.json"
    text = json.dumps(files, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if os.environ.get("UPDATE_SNAPSHOTS") or not snapshot.exists():
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_text(text)
    assert text == snapshot.read_text(), "generated backend changed: review, then rerun with UPDATE_SNAPSHOTS=1"


@pytest.mark.parametrize("name", ["two-entity", "shop"])
def test_every_planned_file_and_test_case_is_generated(name):
    spec = normalized(EXAMPLES / "specs" / f"{name}.json")
    plan = build_plan(spec)
    files = generated(spec)
    for relative, text in files.items():
        if relative.endswith(".py"):
            compile(text, relative, "exec")
    for model in plan["models"]:
        assert model["file"] in files and model["entityFile"] in files
        assert model["class"] in files["src/modules/__init__.py"]
    for module in plan["modules"]:
        port = module["port"]
        for relative in (port["file"], port["implementationFile"], module["router"]["file"], *module["dtoFiles"]):
            assert relative in files, relative
        assert all(usecase["file"] in files for usecase in module["usecases"])
        assert module["router"]["variable"] in files["src/routers.py"]
        tests = files[module["testFile"]]
        for case in module["tests"]:
            assert f"def {case['id']}(client)" in tests, case["id"]


def test_what_the_templates_do_not_cover_is_named():
    plan = build_plan(validate_spec_text(json.dumps(with_custom_operation())).normalized)
    gaps = {module["name"]: codegen_gaps(module) for module in plan["modules"]}
    assert gaps == {"projects": [], "tasks": ["task.complete: custom operation"]}
    assert database_gaps(plan) == []
    one_to_one = copy.deepcopy(plan)
    one_to_one["models"][0]["relationships"][0]["type"] = "one-to-one"
    assert database_gaps(one_to_one) == ["Project.tasks: one-to-one relationships"]


def test_generated_files_are_owned(tmp_path):
    spec = normalized(EXAMPLES / "specs" / "two-entity.json")
    files = generated(spec)
    for relative, text in files.items():
        (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / relative).write_text(text)
    add_owned(tmp_path, list(files))
    assert changed_owned(tmp_path) == []
    router = tmp_path / "src/modules/tasks/presenter/router.py"
    router.write_text(router.read_text() + "\n# edited\n")
    (tmp_path / "src/routers.py").unlink()
    assert changed_owned(tmp_path) == ["src/modules/tasks/presenter/router.py", "src/routers.py"]


# -- the workflow -----------------------------------------------------------------------------------------------------


def test_a_crud_spec_makes_no_backend_engine_call(client, user_headers, tmp_path):
    generation_id = submit(client, user_headers, crudFromTemplates=True)

    assert run_job(tmp_path, generation_id, engine=FakeEngine(tmp_path, demo_scenario(0))) == "COMPLETED"
    assert [c.purpose for c in cli_invocations(generation_id) if c.purpose in ENGINE_STEPS] == []
    summaries = {run.node: run.summary for run in node_runs(generation_id)}
    assert summaries["generate_database"]["engineCalls"] == 0 and summaries["generate_backend"]["engineCalls"] == 0
    assert "generate_tests" not in summaries  # Story 18.11: the template tests come with generate_backend
    assert [run.node for run in node_runs(generation_id)].count("repair_code") == 0  # no planted defect to fix
    parts = [e.payload["part"] for e in events(generation_id) if e.type == "backend.generated"]
    assert parts == ["database", "modules"]
    owned = json.loads((tmp_path / generation_id / "project/.bga/owned.json").read_text())
    for relative in ("src/modules/tasks/presenter/router.py", "src/routers.py", "tests/modules/tasks/test_task_api.py"):
        assert relative in owned
    assert generation(generation_id).status == "COMPLETED"  # the conventions check passed with the owned files


def test_only_what_is_not_crud_goes_to_the_engine(client, user_headers, tmp_path):
    generation_id = submit(client, user_headers, spec=with_custom_operation(), crudFromTemplates=True)
    engine = FakeEngine(tmp_path, demo_scenario(0))

    run_job(tmp_path, generation_id, engine=engine)
    purposes = [c.purpose for c in cli_invocations(generation_id) if c.purpose in ENGINE_STEPS]
    assert purposes == ["complete_backend"]  # the tasks module; its custom op gets a smoke call, not a test
    [complete] = [call for call in engine.calls if call.purpose == "complete_backend"]
    assert "task.complete: custom operation" in complete.prompt
    assert "src/modules/tasks/presenter/router.py" in complete.prompt
    owned = json.loads((tmp_path / generation_id / "project/.bga/owned.json").read_text())
    assert "src/modules/projects/presenter/router.py" in owned  # all CRUD: owned
    assert "src/modules/tasks/presenter/router.py" not in owned  # the engine completes it


def test_date_annotations_are_always_module_qualified():
    """A field named `date` / `datetime` shadows a bare annotation for every later field of the class, so the
    generated code always writes `dt.date` / `dt.datetime` (here `due_date` comes after `date`)."""
    spec = {
        "specVersion": "1.0",
        "project": {"name": "clash-test"},
        "entities": [
            {
                "name": "Expense",
                "table": "expenses",
                "fields": [
                    {"name": "id", "type": "uuid", "primary": True},
                    {"name": "date", "type": "date"},
                    {"name": "due_date", "type": "date", "nullable": True},
                    {"name": "datetime", "type": "datetime"},
                    {"name": "paid_at", "type": "datetime", "nullable": True},
                ],
            }
        ],
        "operations": [],
    }
    plan = build_plan(spec)
    files = database_files(plan)
    model_code = files["src/modules/shared/infrastructure/models/expense_model.py"]
    entity_code = files["src/modules/shared/domain/entities/expense_entity.py"]
    for code in (model_code, entity_code):
        assert "import datetime as dt" in code
        assert "date: dt.date" in code and "due_date: dt.date | None" in code
        assert "datetime: dt.datetime" in code and "paid_at: dt.datetime | None" in code
        assert "from datetime import" not in code
    exec(entity_code, {})
    # The model registers its table on SQLModel's global metadata: drop it again, or the migration drift test
    # (tests/test_migrations.py) finds an `expenses` table no migration creates.
    namespace: dict = {}
    try:
        exec(model_code, namespace)
        assert "ExpenseModel" in namespace
    finally:
        table = SQLModel.metadata.tables.get("expenses")
        if table is not None:
            SQLModel.metadata.remove(table)
    assert "expenses" not in SQLModel.metadata.tables


def test_python_keywords_in_entity_and_field_names_still_compile(tmp_path):
    spec = copy.deepcopy(TWO_ENTITY)
    text = json.dumps(spec).replace('"Project"', '"Class"').replace('"title"', '"from"')
    for old, new in (('"project.', '"class.'), ("/projects", "/classes"), ("projectId", "classId")):
        text = text.replace(old, new)
    (tmp_path / "spec.json").write_text(text)
    files = generated(normalized(tmp_path / "spec.json"))
    for relative, source in files.items():
        if relative.endswith(".py"):
            compile(source, relative, "exec")
    task_model = next(source for relative, source in files.items() if relative.endswith("/task_model.py"))
    assert 'class_: "ClassModel"' in task_model and "from_:" in task_model
    repositories = [source for relative, source in files.items() if relative.endswith("_repository.py")]
    assert repositories and all(source.startswith("from __future__ import annotations") for source in repositories), (
        "a custom `-> list[...]` after the `list` method must not name the method"
    )


def test_entity_indexes_and_unique_constraints_are_in_the_models(tmp_path):
    spec = copy.deepcopy(TWO_ENTITY)
    task = next(entity for entity in spec["entities"] if entity["name"] == "Task")
    task["indexes"] = [{"fields": ["status"]}, {"fields": ["projectId", "dueDate"]}]
    task["uniqueConstraints"] = [["projectId", "title"]]
    (tmp_path / "spec.json").write_text(json.dumps(spec))
    files = generated(normalized(tmp_path / "spec.json"))
    model = next(source for relative, source in files.items() if relative.endswith("/task_model.py"))
    compile(model, "task_model.py", "exec")
    assert 'Index("ix_tasks_project_id_due_date", "project_id", "due_date")' in model
    assert 'UniqueConstraint("project_id", "title", name="uq_tasks_project_id_title")' in model
    assert "index=True" in model.split("status: TaskStatus | None = Field(")[1].split(")")[0], "one column: index=True"
