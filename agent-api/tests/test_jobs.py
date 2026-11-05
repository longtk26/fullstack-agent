"""The jobs plugin (Story 10.6): triggers, events emitted by use cases in the request's transaction, the worker and
its template tests, custom handlers for the engine, the smoke check's worker run."""

import json
from pathlib import Path

from src.orchestrator.backend.codegen import codegen_gaps, database_files, module_files
from src.orchestrator.backend.planner import build_plan
from src.orchestrator.checks.smoke import judge, smoke_calls
from src.orchestrator.integration.contract import build_contract, contract_operations
from src.orchestrator.plugins.app import plugin_files
from tests.generation_helpers import normalized

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


def jobs_spec(tmp_path: Path, custom: bool = False) -> dict:
    """two-entity: a new task and a deleted project are logged by jobs, and a nightly digest runs on cron."""
    raw = json.loads((EXAMPLES / "specs" / "two-entity.json").read_text())
    raw["backgroundJobs"] = [
        {"name": "logNewTask", "trigger": {"event": "task.created"}, "action": "log"},
        {"name": "logRemovedProject", "trigger": "event:project.deleted", "action": "log", "maxAttempts": 3},
        {"name": "nightlyDigest", "trigger": "cron:0 2 * * *", "action": "log"},
        {"name": "tidyUp", "trigger": {"cron": "0 3 * * *"}, "description": "Clean"},  # too vague: not built
    ]
    if custom:
        description = "Email the project's owner when one of its tasks changes"
        raw["backgroundJobs"].append(
            {"name": "notifyOwner", "trigger": {"operation": "task.update"}, "description": description}
        )
    (tmp_path / "jobs-spec.json").write_text(json.dumps(raw))
    return normalized(tmp_path / "jobs-spec.json")


def _module(plan: dict, name: str) -> dict:
    return next(module for module in plan["modules"] if module["name"] == name)


def test_triggers_are_planned_and_crud_operations_emit_only_what_is_subscribed(tmp_path):
    plan = build_plan(jobs_spec(tmp_path, custom=True))
    assert {"name": "jobs", "version": "1"} in plan["plugins"]
    assert [(job["name"], job["trigger"]) for job in plan["jobs"]] == [
        ("logNewTask", {"event": "task.created"}),
        ("logRemovedProject", {"event": "project.deleted"}),
        ("nightlyDigest", {"cron": "0 2 * * *"}),
        ("notifyOwner", {"operation": "task.update"}),
    ]
    emits = {op["operationId"]: op.get("emits") for m in plan["modules"] for op in m["operations"]}
    assert emits["task.create"] == ["task.created"] and emits["task.update"] == ["task.update"]
    assert emits["project.delete"] == ["project.deleted"] and emits["task.delete"] is None
    assert {(entry["ref"], entry["message"].split(":")[0]) for entry in plan["unresolved"]} == {
        ("tidyUp", "Not implemented"),
        ("notifyOwner", "Custom job"),
    }
    assert codegen_gaps(_module(plan, "tasks")) == ["job notifyOwner: custom handler"]
    assert "pluginTables" in plan and "src.libs.jobs.models" in plan["pluginModels"]


def test_use_cases_emit_in_the_requests_transaction(tmp_path):
    spec = jobs_spec(tmp_path)
    plan = build_plan(spec)
    files = module_files(plan, spec, _module(plan, "tasks"))
    create = files["src/modules/tasks/usecases/create_task_usecase.py"]
    assert create.index("self.task_repo.create(") < create.index(
        'jobs.emit("task.created", task.model_dump(mode="json"))'
    )
    assert "jobs: JobQueueDep" in files["src/modules/tasks/presenter/router.py"]
    assert "jobs" not in files["src/modules/tasks/usecases/get_task_usecase.py"]
    delete = module_files(plan, spec, _module(plan, "projects"))[
        "src/modules/projects/usecases/delete_project_usecase.py"
    ]
    assert 'jobs.emit("project.deleted", existing.model_dump(mode="json"))' in delete
    assert "import src.libs.jobs.models  # noqa: F401" in database_files(plan)["src/modules/__init__.py"]


def test_the_project_has_the_queue_the_worker_the_handlers_and_their_tests(tmp_path):
    spec = jobs_spec(tmp_path, custom=True)
    files = plugin_files(build_plan(spec))
    assert 'parser.add_argument("--once"' in files["src/worker.py"]
    assert '@job("logNewTask", events=("task.created",), max_attempts=5)' in files["src/jobs/log_new_task.py"]
    assert '@job("nightlyDigest", cron="0 2 * * *", max_attempts=5)' in files["src/jobs/nightly_digest.py"]
    assert 'raise NotImplementedError("job notifyOwner:' in files["src/jobs/notify_owner.py"]
    assert "tidy_up" not in files["src/jobs/__init__.py"]
    tests = files["tests/modules/jobs/test_jobs.py"]
    for name in (
        "test_a_job_enqueued_in_a_rolled_back_transaction_never_runs",
        "test_a_failing_job_is_retried_then_dead",
        "test_two_workers_never_take_the_same_job",
        "test_a_cron_tick_enqueues_once",
        "test_log_new_task_is_enqueued_on_task_created",
    ):
        assert f"def {name}():" in tests
    for relative, source in files.items():
        if relative.endswith(".py"):
            compile(source, relative, "exec")


def test_the_smoke_check_runs_the_worker_last_and_judges_its_exit(tmp_path):
    spec = jobs_spec(tmp_path)
    plan = build_plan(spec)
    contract = build_contract(spec, plan)
    calls, _ = smoke_calls(contract, plan)
    assert calls[-1] == {"operationId": "jobs.worker", "kind": "worker", "method": "RUN", "path": "src.worker --once"}
    assert judge(contract, [calls[-1]], [{"status": 0, "body": "jobs: 2 ran"}]) == []
    [problem] = judge(contract, [calls[-1]], [{"status": 1, "body": "Traceback ..."}])
    assert "the job worker failed" in problem["message"]
    ops = {op_id: found["operation"] for op_id, found in contract_operations(contract).items()}
    assert ops["task.create"]["x-bga"]["emits"] == ["task.created"]
    assert [job["name"] for job in contract["x-bga"]["jobs"]] == ["logNewTask", "logRemovedProject", "nightlyDigest"]


def test_job_triggers_are_validated():
    from src.modules.shared.domain.backend_spec.validator import validate_spec_data

    raw = json.loads((EXAMPLES / "specs" / "two-entity.json").read_text())
    raw["backgroundJobs"] = [
        {"name": "a", "trigger": {"event": "invoice.created"}},
        {"name": "b", "trigger": {"operation": "task.nope"}},
        {"name": "c", "trigger": "cron:every day"},
        {"name": "d", "trigger": {"event": "task.created", "cron": "0 2 * * *"}},
    ]
    paths = {issue.path for issue in validate_spec_data(raw).report.errors}
    assert paths == {
        "/backgroundJobs/0/trigger/event",
        "/backgroundJobs/1/trigger/operation",
        "/backgroundJobs/2/trigger/cron",
        "/backgroundJobs/3/trigger",
    }
