import asyncio
import json

import pytest
from redis.asyncio import Redis

from src.configs import config
from src.libs.queue import JobQueue
from src.libs.redaction import Redactor
from src.modules.generations.infrastructure.adapters import EventPublisher
from workflow_helpers import TWO_ENTITY, generation, run_job, submit

pytestmark = pytest.mark.usefixtures("clean_redis")


def _queued() -> list[str]:
    async def read():
        client = Redis.from_url(config.redis_url, decode_responses=True)
        try:
            jobs = []
            async for key in client.scan_iter(match="bga:jobs:*"):
                jobs += await client.lrange(key, 0, -1)
            return jobs
        finally:
            await client.aclose()

    return asyncio.run(read())


def test_submit_returns_202_and_enqueues(client, user_headers):
    response = client.post(
        "/api/v1/generations",
        json={"backendSpec": TWO_ENTITY, "options": {"engine": "fake", "crudFromTemplates": False}},
        headers=user_headers,
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "PENDING" and body["generationId"].startswith("gen_")
    assert _queued() == [body["generationId"]]
    row = generation(body["generationId"])
    assert row.options["maxRepairAttempts"] == 3 and row.engine == "fake"


def test_submit_by_spec_id_and_default_engine(client, user_headers):
    spec_id = client.post(
        "/api/v1/specs", content=json.dumps(TWO_ENTITY), headers={**user_headers, "content-type": "application/json"}
    ).json()["specId"]

    response = client.post(
        "/api/v1/generations", json={"specId": spec_id, "options": {"deployPreview": False}}, headers=user_headers
    )

    assert response.status_code == 202
    assert generation(response.json()["generationId"]).engine == config.default_engine


@pytest.mark.parametrize(
    ("body", "code"),
    [
        (
            {"backendSpec": TWO_ENTITY, "options": {"deployPreview": True, "generateDockerfile": False}},
            "OPTIONS_CONFLICT",
        ),
        ({"options": {}}, "MODE_INPUT_MISMATCH"),
        ({"backendSpec": TWO_ENTITY, "specId": "00000000-0000-0000-0000-000000000000"}, "MODE_INPUT_MISMATCH"),
        ({"backendSpec": TWO_ENTITY, "options": {"engine": "gpt"}}, "VALIDATION_ERROR"),
        ({"backendSpec": TWO_ENTITY, "options": {"maxRepairAttempts": 11}}, "VALIDATION_ERROR"),
        ({"backendSpec": TWO_ENTITY, "options": {"colour": "red"}}, "VALIDATION_ERROR"),
    ],
)
def test_submit_rejects_bad_requests(client, user_headers, body, code):
    response = client.post("/api/v1/generations", json=body, headers=user_headers)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == code


def test_invalid_inline_spec_is_accepted_and_fails_later(client, user_headers, tmp_path):
    generation_id = submit(client, user_headers, spec={"specVersion": "1.0", "project": {}})

    assert run_job(tmp_path, generation_id) == "FAILED"


def test_idempotency_key_returns_the_same_generation(client, user_headers):
    headers = {**user_headers, "Idempotency-Key": "abc-123"}
    body = {
        "backendSpec": TWO_ENTITY,
        "options": {"engine": "fake", "deployPreview": False, "crudFromTemplates": False},
    }

    first = client.post("/api/v1/generations", json=body, headers=headers).json()["generationId"]
    second = client.post("/api/v1/generations", json=body, headers=headers).json()["generationId"]

    assert first == second
    assert _queued() == [first]


def test_detail_and_ownership(client, user_headers, login, tmp_path):
    generation_id = submit(client, user_headers)
    run_job(tmp_path, generation_id)
    other = {"Authorization": f"Bearer {login('other@test.local', 'otherpass')}"}

    detail = client.get(f"/api/v1/generations/{generation_id}", headers=user_headers).json()

    assert detail["status"] == "COMPLETED"
    assert detail["projectName"] == "Project Tracker"
    assert detail["validation"]["syntax"] == "passed"
    assert [s["node"] for s in detail["steps"]][:2] == ["validate_spec", "plan_architecture"]
    assert detail["repairAttempts"] == 1
    by_node = {s["node"]: s for s in detail["steps"]}
    assert [i["purpose"] for i in by_node["generate_backend"]["invocations"]] == ["generate_backend"] * 2
    assert by_node["validate_spec"]["invocations"] == []
    assert set(detail["usage"]) == {"inputTokens", "outputTokens", "costUsd"}
    assert client.get(f"/api/v1/generations/{generation_id}", headers=other).status_code == 404


def test_list_paginates_and_filters(client, login):
    headers = {"Authorization": f"Bearer {login('other@test.local', 'otherpass')}"}
    ids = [submit(client, headers) for _ in range(3)]

    first = client.get("/api/v1/generations?limit=2", headers=headers).json()
    second = client.get(f"/api/v1/generations?limit=2&cursor={first['nextCursor']}", headers=headers).json()
    pending = client.get("/api/v1/generations?status=PENDING&limit=100", headers=headers).json()

    listed = [item["generationId"] for item in first["items"] + second["items"]]
    assert listed[:3] == list(reversed(ids)), "newest first"
    assert first["items"][0]["projectName"] == "Project Tracker"
    assert {i["generationId"] for i in pending["items"]} >= set(ids)


def test_scope_all_is_admin_only(client, user_headers, login):
    admin = {"Authorization": f"Bearer {login('admin@test.local', 'adminpass')}"}

    assert client.get("/api/v1/generations?scope=all", headers=user_headers).status_code == 403
    assert client.get("/api/v1/generations?scope=all", headers=admin).status_code == 200


def test_cancel_pending_job_removes_it_from_the_queue(client, user_headers):
    generation_id = submit(client, user_headers)

    response = client.post(f"/api/v1/generations/{generation_id}/cancel", headers=user_headers)

    assert response.status_code == 202
    assert response.json()["status"] == "CANCELLED"
    assert _queued() == []
    again = client.post(f"/api/v1/generations/{generation_id}/cancel", headers=user_headers)
    assert again.status_code == 409 and again.json()["error"]["code"] == "ALREADY_FINISHED"


def test_cancel_running_job_sets_the_flag(client, user_headers):
    generation_id = submit(client, user_headers)
    asyncio.run(_drain_queue())  # as if a worker had taken it

    response = client.post(f"/api/v1/generations/{generation_id}/cancel", headers=user_headers)

    assert response.json()["cancelRequested"] is True
    assert generation(generation_id).cancel_requested is True


async def _drain_queue():
    client = Redis.from_url(config.redis_url, decode_responses=True)
    try:
        await JobQueue(client).dequeue("w-test", ["fake", "claude_code"], 1)
    finally:
        await client.aclose()


def test_graph_describes_the_workflow(client, user_headers):
    graph = client.get("/api/v1/generations/graph", headers=user_headers).json()

    node_ids = [n["id"] for n in graph["nodes"]]
    assert node_ids[1:-1] == [
        "validate_spec",
        "plan_architecture",
        "generate_database",
        "generate_backend",
        "generate_tests",
        "run_validation",
        "repair_code",
        "package_artifacts",
    ]
    labels = {(e["source"], e["target"]): e["label"] for e in graph["edges"] if e["conditional"]}
    assert labels[("run_validation", "repair_code")] == "failed"
    assert next(n for n in graph["nodes"] if n["id"] == "repair_code")["status"] == "REPAIRING"


def _sse_events(client, generation_id, headers):
    collected = []
    with client.stream("GET", f"/api/v1/generations/{generation_id}/events", headers=headers) as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if line.startswith("data:"):
                collected.append(json.loads(line[5:].strip()))
    return collected


def test_sse_replays_everything_and_closes_after_the_terminal_status(client, user_headers, tmp_path):
    generation_id = submit(client, user_headers)
    run_job(tmp_path, generation_id)

    streamed = _sse_events(client, generation_id, user_headers)

    assert streamed[0]["status"] == "PENDING"
    assert streamed[-1]["type"] == "status.changed" and streamed[-1]["status"] == "COMPLETED"
    assert [e["id"] for e in streamed] == sorted(e["id"] for e in streamed)
    assert {"step.started", "engine.event", "validation.check", "repair.attempt"} <= {e["type"] for e in streamed}


def test_sse_resumes_after_last_event_id(client, user_headers, tmp_path):
    generation_id = submit(client, user_headers)
    run_job(tmp_path, generation_id)
    everything = _sse_events(client, generation_id, user_headers)

    tail = _sse_events(client, generation_id, {**user_headers, "Last-Event-ID": str(everything[-4]["id"])})

    assert [e["id"] for e in tail] == [e["id"] for e in everything[-3:]]


def test_sse_payloads_are_redacted(client, user_headers):
    generation_id = submit(client, user_headers)

    async def publish():
        redis = Redis.from_url(config.redis_url, decode_responses=True)
        try:
            publisher = EventPublisher(redis, Redactor(["topsecretvalue123"]))
            await publisher.publish(generation_id, "log", payload={"line": "key topsecretvalue123"})
            await publisher.publish(generation_id, "status.changed", status="CANCELLED")
        finally:
            await redis.aclose()

    asyncio.run(publish())
    streamed = _sse_events(client, generation_id, user_headers)

    assert "topsecretvalue123" not in json.dumps(streamed)


def test_sse_requires_ownership(client, user_headers, login):
    generation_id = submit(client, user_headers)
    other = {"Authorization": f"Bearer {login('other@test.local', 'otherpass')}"}

    assert client.get(f"/api/v1/generations/{generation_id}/events", headers=other).status_code == 404
