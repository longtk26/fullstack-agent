import asyncio
import subprocess

import pytest
from sqlmodel import Session

from src.engines import EngineHealth, EngineStatus
from src.engines.fake_engine import DEMO_SCENARIO, FakeEngine, FakeStep, SimulatedCrash
from src.libs.database import db_session_manager
from src.modules.shared.infrastructure.models import GenerationModel
from src.orchestrator.checkpointer import postgres_checkpointer
from workflow_helpers import (
    TWO_ENTITY,
    cli_invocations,
    events,
    generation,
    node_runs,
    redis_client,
    run_job,
    runner_ctx,
    statuses,
    submit,
)

pytestmark = pytest.mark.usefixtures("clean_redis")


def test_demo_run_goes_through_one_repair_and_completes(client, user_headers, tmp_path):
    generation_id = submit(client, user_headers)

    assert run_job(tmp_path, generation_id) == "COMPLETED"

    assert statuses(generation_id) == [
        "PENDING",
        "RUNNING",
        "VALIDATING",
        "REPAIRING",
        "VALIDATING",
        "RUNNING",
        "COMPLETED",
    ]
    row = generation(generation_id)
    assert row.repair_attempts == 1 and row.finished_at is not None and row.error_summary is None
    runs = [(r.node, r.attempt, r.status) for r in node_runs(generation_id)]
    assert runs == [
        ("validate_spec", 1, "succeeded"),
        ("plan_architecture", 1, "succeeded"),
        ("generate_database", 1, "succeeded"),
        ("generate_backend", 1, "succeeded"),
        ("generate_tests", 1, "succeeded"),
        ("run_validation", 1, "failed"),
        ("repair_code", 1, "succeeded"),
        ("run_validation", 2, "succeeded"),
        ("package_artifacts", 1, "succeeded"),
    ]
    purposes = sorted(i.purpose for i in cli_invocations(generation_id))
    # two-entity spec = two modules, so backend and tests run once per module
    assert purposes == ["generate_backend"] * 2 + ["generate_database"] + ["generate_tests"] * 2 + ["repair_code"]
    assert all(i.status == "ok" and i.node_run_id is not None for i in cli_invocations(generation_id))

    project = tmp_path / generation_id / "project"
    assert (project / ".bga" / "spec.json").exists() and (project / ".bga" / "plan.json").exists()
    log = subprocess.run(["git", "log", "--format=%s"], cwd=project, capture_output=True, text=True).stdout
    assert "node:repair_code attempt:1" in log and "node:package_artifacts attempt:1" in log
    checks = {e.payload["check"]: e.status for e in events(generation_id) if e.type == "validation.check"}
    assert checks["syntax"] == "passed" and checks["tests"] == "not_run", "unexecuted checks are never 'passed'"


def test_invalid_spec_fails_without_calling_the_engine(client, user_headers, tmp_path):
    spec = {**TWO_ENTITY, "operations": [{**TWO_ENTITY["operations"][0], "method": "GET"}]}
    generation_id = submit(client, user_headers, spec=spec)

    assert run_job(tmp_path, generation_id) == "FAILED"

    row = generation(generation_id)
    assert row.error_summary.startswith("BackendSpec has 1 error(s)")
    assert cli_invocations(generation_id) == []
    final = events(generation_id)[-1]
    assert final.type == "status.changed" and final.payload["errorCode"] == "SPEC_INVALID"
    assert any(e.type == "spec.invalid" for e in events(generation_id))


def test_repair_limit_fails_with_a_diagnostic(client, user_headers, tmp_path):
    broken = {"src/x.py": "def broken(:\n"}
    engine = FakeEngine(tmp_path, {**DEMO_SCENARIO, "repair_code": [FakeStep(write=broken)], "*": [FakeStep()]})
    generation_id = submit(client, user_headers, maxRepairAttempts=2)

    assert run_job(tmp_path, generation_id, engine=engine) == "FAILED"

    row = generation(generation_id)
    assert row.repair_attempts == 2
    assert "after 2 repair attempt(s): syntax" in row.error_summary
    assert events(generation_id)[-1].payload["errorCode"] == "REPAIR_LIMIT"
    assert [r.node for r in node_runs(generation_id)].count("run_validation") == 3


def test_run_tests_false_skips_test_generation(client, user_headers, tmp_path):
    generation_id = submit(client, user_headers, runTests=False)

    assert run_job(tmp_path, generation_id) == "COMPLETED"

    tests_step = next(r for r in node_runs(generation_id) if r.node == "generate_tests")
    assert tests_step.status == "skipped"
    assert "generate_tests" not in {i.purpose for i in cli_invocations(generation_id)}


class UnavailableEngine(FakeEngine):
    async def health(self):
        return EngineHealth(name=self.name, available=False, reason="no credentials")


def test_unavailable_engine_fails_fast(client, user_headers, tmp_path):
    generation_id = submit(client, user_headers)

    assert run_job(tmp_path, generation_id, engine=UnavailableEngine(tmp_path)) == "FAILED"

    assert "no credentials" in generation(generation_id).error_summary
    assert events(generation_id)[-1].payload["errorCode"] == "ENGINE_UNAVAILABLE"


def test_engine_failure_is_reported_as_engine_error(client, user_headers, tmp_path):
    engine = FakeEngine(tmp_path, {"*": [FakeStep(status=EngineStatus.CLI_ERROR)]})
    generation_id = submit(client, user_headers)

    assert run_job(tmp_path, generation_id, engine=engine) == "FAILED"

    assert events(generation_id)[-1].payload["errorCode"] == "ENGINE_ERROR"


def test_cancel_stops_a_running_engine_call(client, user_headers, tmp_path):
    engine = FakeEngine(tmp_path, {"*": [FakeStep(sleep_s=30)]})
    generation_id = submit(client, user_headers)

    async def scenario():
        async with runner_ctx(tmp_path, engine=engine) as runner:
            task = asyncio.create_task(runner.run(generation_id))
            for _ in range(50):
                await asyncio.sleep(0.1)
                if runner.active.get(generation_id) and runner.active[generation_id].current_invocation:
                    break
            assert await runner.cancel(generation_id)
            return await asyncio.wait_for(task, timeout=10)

    assert asyncio.run(scenario()) == "CANCELLED"
    assert node_runs(generation_id)[-1].status == "cancelled"
    assert statuses(generation_id)[-1] == "CANCELLED"


def test_job_timeout_fails_the_job(client, user_headers, tmp_path):
    engine = FakeEngine(tmp_path, {"*": [FakeStep(sleep_s=30)]})
    generation_id = submit(client, user_headers)
    with Session(db_session_manager.engine) as session:
        row = session.get(GenerationModel, generation_id)
        row.options = {**row.options, "timeoutSeconds": 1}
        session.add(row)
        session.commit()

    assert run_job(tmp_path, generation_id, engine=engine) == "FAILED"

    assert events(generation_id)[-1].payload["errorCode"] == "TIMEOUT"


def test_crash_then_resume_from_postgres_checkpoint(client, user_headers, tmp_path):
    scenario = {**DEMO_SCENARIO, "generate_backend": [FakeStep(crash=True), *DEMO_SCENARIO["generate_backend"]]}
    engine = FakeEngine(tmp_path, scenario)
    generation_id = submit(client, user_headers)
    project = tmp_path / generation_id / "project"

    async def first_attempt():
        async with postgres_checkpointer() as saver, runner_ctx(tmp_path, engine=engine, checkpointer=saver) as runner:
            await runner.run(generation_id)

    with pytest.raises(SimulatedCrash):
        asyncio.run(first_attempt())
    (project / "half-written.py").write_text("partial output of the crashed node")
    assert generation(generation_id).status == "RUNNING", "a crash leaves the job active for the reaper"

    async def resume():
        async with postgres_checkpointer() as saver, runner_ctx(tmp_path, engine=engine, checkpointer=saver) as runner:
            return await runner.run(generation_id)

    assert asyncio.run(resume()) == "COMPLETED"

    purposes = [call.purpose for call in engine.calls]
    assert purposes.count("generate_database") == 1, "completed nodes are not re-run"
    assert not (project / "half-written.py").exists(), "workspace was reset to the last completed node"
    assert any(e.type == "job.resumed" for e in events(generation_id))
    assert "abandoned" in {r.status for r in node_runs(generation_id)}


def test_redis_helper_connects():
    async def ping():
        client = redis_client()
        try:
            return await client.ping()
        finally:
            await client.aclose()

    assert asyncio.run(ping())


def test_antigravity_jobs_get_a_longer_default_timeout():
    from src.configs import config
    from src.orchestrator.runner import job_timeout

    assert job_timeout("claude_code") == config.job_timeout_seconds
    assert job_timeout("antigravity") == config.antigravity_job_timeout_seconds > config.job_timeout_seconds
