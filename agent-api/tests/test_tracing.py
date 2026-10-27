"""Stories 8.1–8.4: LangSmith span tree, secret masking, trace id correlation, local trace and usage APIs."""

import json

import pytest
from tracing_fakes import RecordingLangSmithClient

from src.configs import config
from src.engines.fake_engine import FakeEngine, demo_scenario
from src.orchestrator import tracing
from workflow_helpers import events, generation, run_job, submit

pytestmark = pytest.mark.usefixtures("clean_redis")
PLANTED = "sk-ant-api03-PLANTEDSECRETPLANTEDSECRET"


@pytest.fixture
def langsmith(monkeypatch):
    """Tracing on, with the recording client in place of LangSmith."""
    created: list[RecordingLangSmithClient] = []

    def client_factory(**kwargs):
        created.append(RecordingLangSmithClient(**kwargs))
        return created[-1]

    monkeypatch.setattr(config, "langsmith_tracing", True)
    monkeypatch.setattr(config, "langsmith_api_key", "lsv2_pt_" + "k" * 32)
    monkeypatch.setattr(config, "langsmith_agent_id", None)
    monkeypatch.setattr(tracing, "_client", None)
    monkeypatch.setattr("langsmith.Client", client_factory)
    yield created
    tracing._client = None


def _planted_scenario():
    scenario = demo_scenario(0)
    [repair] = scenario["repair_code"]
    scenario["repair_code"] = [repair.model_copy(update={"write": {**repair.write, f"notes/{PLANTED}.md": "x"}})]
    return scenario


def test_a_generation_is_one_trace_with_the_epic_8_shape(client, user_headers, tmp_path, langsmith):
    generation_id = submit(client, user_headers)
    assert run_job(tmp_path, generation_id, engine=FakeEngine(tmp_path, _planted_scenario())) == "COMPLETED"

    recorder = langsmith[0]
    assert recorder.kwargs["hide_inputs"] is tracing.redact_for_trace
    [root] = recorder.named("backend-generation")
    assert root.get("parent_run_id") is None and root["session_name"] == config.langsmith_project
    metadata = root["extra"]["metadata"]
    assert metadata["generation_id"] == generation_id and metadata["engine"] == "fake"
    assert len(metadata["spec_sha256"]) == 64 and metadata["prompt_versions"]["repair_code"] == "v3"
    assert root["outputs"]["status"] == "COMPLETED" and root["outputs"]["validation"]["syntax"] == "passed"
    assert "fake" in root["tags"]

    nodes = {run["name"] for run in recorder.children(root["id"])}
    assert {"validate_spec", "generate_backend", "run_validation#1", "repair_code#1", "run_validation#2"} <= nodes
    [repair] = recorder.named("repair_code#1")
    assert repair["outputs"]["diffStats"]["files"] == 2
    [failed_validation] = recorder.named("run_validation#1")
    checks = {run["name"]: run for run in recorder.children(failed_validation["id"])}
    assert checks["check:syntax"]["error"].startswith("failed") and "check:conventions" in checks

    engines = recorder.named("engine:fake")
    assert len(engines) == 6 and all(run["run_type"] == "tool" for run in engines)
    assert engines[0]["inputs"]["prompt"] == "generate_database@v2"
    calls = recorder.children(engines[0]["id"])
    assert [run["name"] for run in calls] == ["llm:fake #1", "llm:fake #2"]
    usage = calls[0]["extra"]["metadata"]["usage_metadata"]
    assert usage["input_tokens"] == 600 and usage["total_cost"] == 0.0
    assert calls[0]["extra"]["metadata"]["ls_model_name"] == "fake"
    assert [run["name"] for run in recorder.children(calls[0]["id"])] == ["tool:Copy database"]

    stored = generation(generation_id)
    assert stored.trace_id == str(root["id"]) and stored.langsmith_run_url.startswith("https://smith.test/")
    traced = json.dumps(list(recorder.runs.values()), default=str)
    assert PLANTED not in traced and config.langsmith_api_key not in traced
    worker_events = [e for e in events(generation_id) if e.type != "status.changed" or e.status != "PENDING"]
    assert worker_events and all(e.payload.get("traceId") == stored.trace_id for e in worker_events)
    assert PLANTED not in json.dumps([e.payload for e in events(generation_id)])


def test_trace_redaction_masks_secrets_and_cuts_long_text():
    data = {"prompt": "token sk-ant-api03-ABCDEFGHIJKLMNOP and " + "x" * 6000, "jwt": config.jwt_secret}

    hidden = tracing.redact_for_trace(data)

    assert "sk-ant-api03-ABCDEFGHIJKLMNOP" not in hidden["prompt"] and len(hidden["prompt"]) < 4200
    assert config.jwt_secret not in hidden["jwt"]


def test_agent_address_replaces_the_project(monkeypatch):
    monkeypatch.setattr(config, "langsmith_agent_id", "fullstack-agent")
    monkeypatch.setattr(config, "langsmith_agent_environment", "local")

    assert tracing.destination() == {"address": {"kind": "AGENT", "id": "fullstack-agent", "environment": "LOCAL"}}


def test_without_tracing_the_job_still_has_a_trace_id(client, user_headers, tmp_path):
    generation_id = submit(client, user_headers)
    assert run_job(tmp_path, generation_id, engine=FakeEngine(tmp_path, demo_scenario(0))) == "COMPLETED"

    stored = generation(generation_id)
    assert stored.trace_id and stored.langsmith_run_url is None


def test_local_trace_and_usage(client, user_headers, login, tmp_path):
    admin_headers = {"Authorization": f"Bearer {login('admin@test.local', 'adminpass')}"}
    generation_id = submit(client, user_headers)
    assert run_job(tmp_path, generation_id, engine=FakeEngine(tmp_path, _planted_scenario())) == "COMPLETED"

    trace = client.get(f"/api/v1/generations/{generation_id}/trace", headers=user_headers).json()
    spans = {span["spanId"]: span for span in trace["spans"]}
    assert all(span["parentId"] in spans for span in spans.values() if span["parentId"])
    kinds = {span["kind"] for span in spans.values()}
    assert {"generation", "node", "engine", "llm", "tool", "check"} <= kinds
    llm = next(span for span in spans.values() if span["kind"] == "llm")
    assert spans[llm["parentId"]]["kind"] == "engine" and llm["attrs"]["model"] == "fake"
    repair = next(span for span in spans.values() if span["name"] == "repair_code#1")
    assert repair["refs"]["patch"] and repair["attrs"]["diffStats"]["files"] == 2
    assert PLANTED not in json.dumps(trace)

    usage = trace["usage"]
    assert usage["engineCalls"] == 6 and usage["modelCalls"] == 12
    assert usage["tokens"]["input"] == 6000 and usage["cost"] == {
        "reported": 0.0,
        "estimated": 0.0,
        "total": 0.0,
        "unpriced": 0,
    }
    by_node = {row["node"]: row for row in usage["byNode"]}
    assert by_node["generate_backend"]["engineCalls"] == 2 and by_node["repair_code"]["attempts"] == 1
    assert usage["byModel"][0]["model"] == "fake"

    output = client.get(
        f"/api/v1/generations/{generation_id}/trace/spans/{repair['spanId']}/output", headers=user_headers
    ).json()
    assert output["stream"] == "patch" and "router.py" in output["text"]
    missing = client.get(f"/api/v1/generations/{generation_id}/trace/spans/llm:nope/output", headers=user_headers)
    assert missing.status_code == 404

    report = client.get(f"/api/v1/generations/{generation_id}/usage", headers=user_headers).json()
    assert report["modelCalls"] == 12

    totals = client.get("/api/v1/usage", headers=user_headers).json()
    assert totals["totals"]["generations"] >= 1 and any(
        r["generationId"] == generation_id for r in totals["generations"]
    )
    assert any(row["node"] == "run_validation" for row in totals["byNode"])
    assert len(totals["byDay"]) == 7
    assert client.get("/api/v1/usage?scope=all", headers=user_headers).status_code == 403
    assert client.get("/api/v1/usage?scope=all", headers=admin_headers).status_code == 200
    assert client.get("/api/v1/usage?from=2026-10-10&to=2026-10-01", headers=user_headers).status_code == 400


def test_trace_is_owner_scoped(client, user_headers, login, tmp_path):
    generation_id = submit(client, user_headers)
    other = {"Authorization": f"Bearer {login('other@test.local', 'otherpass')}"}

    assert client.get(f"/api/v1/generations/{generation_id}/trace", headers=other).status_code == 404
    assert client.get(f"/api/v1/generations/{generation_id}/usage", headers=other).status_code == 404


def test_running_spans_have_no_end():
    import uuid
    from datetime import UTC, datetime

    from src.modules.shared.domain.entities import CliInvocationEntity, GenerationEntity, NodeRunEntity
    from src.modules.shared.domain.enums import GenerationStatus
    from src.modules.shared.domain.telemetry import ExecutionRecords, build_spans, rollup

    now = datetime.now(UTC)
    generation = GenerationEntity(
        id="gen_x",
        owner_id=uuid.uuid4(),
        spec_id=uuid.uuid4(),
        engine="fake",
        status=GenerationStatus.RUNNING,
        created_at=now,
        started_at=now,
    )
    node = NodeRunEntity(
        id=uuid.uuid4(), generation_id="gen_x", node="generate_backend", status="running", started_at=now
    )
    invocation = CliInvocationEntity(
        id=uuid.uuid4(),
        generation_id="gen_x",
        node_run_id=node.id,
        engine="fake",
        purpose="generate_backend",
        status="running",
        created_at=now,
    )
    records = ExecutionRecords(generation=generation, node_runs=[node], invocations=[invocation])

    spans = {span["kind"]: span for span in build_spans(records)}

    assert spans["generation"]["endedAt"] is None and spans["node"]["endedAt"] is None
    assert spans["engine"]["endedAt"] is None and spans["engine"]["parentId"] == spans["node"]["spanId"]
    assert rollup(records)["byNode"][0]["engineCalls"] == 1


def test_log_lines_carry_the_job_context():
    import logging

    from src.configs import log_context
    from src.configs.logger import JsonFormatter

    token = log_context.set({"generation_id": "gen_1", "trace_id": "t-1"})
    try:
        record = logging.LogRecord("bga", logging.INFO, __file__, 1, "step", (), None)
        payload = json.loads(JsonFormatter().format(record))
    finally:
        log_context.reset(token)

    assert payload["generation_id"] == "gen_1" and payload["trace_id"] == "t-1"
