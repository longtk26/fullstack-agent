"""Story 17.6: the CRUD parts of a backend (models, modules, tests) written from templates, without the engine."""

import copy
import json
import os
from pathlib import Path

import pytest
from generation_helpers import EXAMPLES, normalized

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
ENGINE_STEPS = ("generate_database", "generate_backend", "complete_backend", "generate_tests")


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
    assert summaries["generate_tests"]["engineCalls"] == 0
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
    assert purposes == ["complete_backend", "generate_tests"]  # the tasks module, and the custom op's test
    [complete] = [call for call in engine.calls if call.purpose == "complete_backend"]
    assert "task.complete: custom operation" in complete.prompt
    assert "src/modules/tasks/presenter/router.py" in complete.prompt
    owned = json.loads((tmp_path / generation_id / "project/.bga/owned.json").read_text())
    assert "src/modules/projects/presenter/router.py" in owned  # all CRUD: owned
    assert "src/modules/tasks/presenter/router.py" not in owned  # the engine completes it
