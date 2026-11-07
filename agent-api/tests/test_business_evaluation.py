"""Story 26.5: the business evaluation's checker against a fake backend (no network, no model), and its isolation from
the generation (information only, Epic 26 D4)."""

import asyncio
import json
import uuid
from types import SimpleNamespace
from typing import Any

import pytest

from src.orchestrator.evaluation import api as api_module
from src.orchestrator.evaluation.api import Api
from src.orchestrator.evaluation.checker import Checker, score
from src.orchestrator.evaluation.service import EvaluationService

STEP = {"rule": "", "delivers": []}
BUSINESS = {
    "actors": [
        {"id": "member", "name": "Member", "description": "", "signsIn": True},
        {"id": "staff", "name": "Staff", "description": "", "signsIn": True},
    ],
    "workflows": [
        {
            "id": "handle",
            "name": "Handle a request",
            "steps": [
                {
                    **STEP,
                    "id": "ask",
                    "actor": "member",
                    "action": "submit a request",
                    "record": "request",
                    "statusAfter": "open",
                },  # fmt: skip
                {
                    **STEP,
                    "id": "close",
                    "actor": "staff",
                    "action": "close it",
                    "record": "request",
                    "statusAfter": "closed",
                },  # fmt: skip
            ],
            "branches": [],
        }
    ],
}
EXPECTED = {
    "paths": [
        {
            "workflow": "handle",
            "path": "main",
            "steps": [
                {
                    "step": "ask",
                    "allowed": ["member"],
                    "refused": [],
                    "record": "request",
                    "statusAfter": "open",
                    "visibleTo": ["member"],
                    "hiddenFrom": ["other:member"],
                    "effects": [],
                    "refusedBefore": [],
                },  # fmt: skip
                {
                    "step": "close",
                    "allowed": ["staff"],
                    "refused": ["member"],
                    "record": "request",
                    "statusAfter": "closed",
                    "visibleTo": [],
                    "hiddenFrom": [],
                    "effects": [],
                    "refusedBefore": [],
                },  # fmt: skip
            ],
            "outcome": [],
        }
    ]
}
BINDING = {
    "actors": [{"actor": "member", "role": "member"}, {"actor": "staff", "role": "staff"}],
    "records": [
        {
            "record": "request",
            "entity": "Request",
            "getOperation": "request.get",
            "listOperation": "",
            "statusField": "status",
            "statuses": [{"business": "open", "value": "OPEN"}, {"business": "closed", "value": "CLOSED"}],
        }
    ],  # fmt: skip
    "setup": [],
    "steps": [
        {
            "workflow": "handle",
            "path": "main",
            "step": "ask",
            "operationId": "request.create",
            "pathParamsJson": "",
            "queryJson": "",
            "bodyJson": '{"title": "t-{{run}}"}',
            "creates": "request",
            "automatic": False,
            "page": "",
            "pageParamsJson": "",
        },  # fmt: skip
        {
            "workflow": "handle",
            "path": "main",
            "step": "close",
            "operationId": "request.close",
            "pathParamsJson": '{"id": "{{request}}"}',
            "queryJson": "",
            "bodyJson": "",
            "creates": "",
            "automatic": False,
            "page": "",
            "pageParamsJson": "",
        },  # fmt: skip
    ],
    "effects": [],
    "outcomes": [],
}
OPERATIONS = [
    {"operationId": "request.create", "method": "POST", "path": "/requests"},
    {"operationId": "request.get", "method": "GET", "path": "/requests/{id}"},
    {"operationId": "request.close", "method": "POST", "path": "/requests/{id}/close"},
]
USERS = {"demo-member@example.com": "member", "demo-member-2@example.com": "member", "demo-staff@example.com": "staff"}
AUTH = {
    "login": "/auth/login", "field": "email", "password": "demo12345", "signIn": "/login", "me": "/auth/me",
    "register": "/auth/register",
    "roles": {"member": ["demo-member@example.com", "demo-member-2@example.com"], "staff": ["demo-staff@example.com"]},
}  # fmt: skip


class Response:
    def __init__(self, status: int, data: Any):
        self.status_code = status
        self._data = data
        self.text = json.dumps(data)

    def json(self) -> Any:
        return self._data


class FakeBackend:
    """Members own requests; staff close them. `bugs` switches on the lab's failure cases."""

    def __init__(self, bugs: set[str] = frozenset()):
        self.bugs = bugs
        self.records: dict[str, dict[str, Any]] = {}

    def __call__(self, method: str, url: str, json=None, headers=None, params=None, timeout=None) -> Response:
        path = url.split("://", 1)[1].split("/", 1)[1]
        path = "/" + path
        user = (headers or {}).get("Authorization", "").removeprefix("Bearer ") or None
        role = USERS.get(user or "")
        if path == "/auth/login":
            return Response(200, {"accessToken": json["email"]}) if json["email"] in USERS else Response(401, {})
        if path == "/auth/me":
            return Response(200, {"id": user, "role": role}) if role else Response(401, {})
        if path == "/requests" and method == "POST":
            record = {"id": uuid.uuid4().hex, "title": json["title"], "status": "OPEN", "owner": user}
            self.records[record["id"]] = record
            return Response(201, record)
        parts = path.strip("/").split("/")
        if method == "GET" and (parts[0] == "desk" or parts[:2] == ["requests", "desk"]):
            # staff's own read of a request (as `GET /repair-requests/jobs/{id}`), under /desk or /requests/desk
            record = self.records.get(parts[-1])
            if record is None:
                return Response(404, {"error": "not found"})
            return Response(200, record) if role == "staff" else Response(404, {"error": "not found"})
        record = self.records.get(parts[1]) if len(parts) > 1 else None
        if record is None:
            return Response(404, {"error": "not found"})
        if len(parts) == 2 and method == "GET":
            staff = role == "staff" and "staff_reads_at_desk" not in self.bugs
            mine = record["owner"] == user or staff or "everyone_reads" in self.bugs
            return Response(200, record) if mine else Response(404, {"error": "not found"})
        if parts[2:] == ["close"]:
            if role != "staff" and "anyone_closes" not in self.bugs:
                return Response(403, {"error": "forbidden"})
            if record["status"] != "OPEN":
                return Response(409, {"error": "already closed"})
            record["status"] = "CLOSED"
            return Response(200, record)
        return Response(404, {})


@pytest.fixture
def backend(monkeypatch):
    def install(bugs=frozenset()):
        fake = FakeBackend(set(bugs))
        stub = SimpleNamespace(
            post=lambda url, json=None, headers=None, timeout=None: fake("POST", url, json, headers),
            get=lambda url, headers=None, timeout=None, params=None: fake("GET", url, None, headers),
            request=lambda method, url, params=None, json=None, headers=None, timeout=None: fake(
                method, url, json, headers
            ),
            HTTPError=Exception,
        )
        monkeypatch.setattr(api_module, "httpx", stub)
        return fake

    return install


def _check(binding=BINDING, expected=EXPECTED):
    checker = Checker(
        api=Api("http://localhost:9999", AUTH, OPERATIONS),
        second_look=None,
        log=lambda line: None,
        business=BUSINESS,
        expected=expected,
        binding=binding,
        walker=None,
        frontend="",
        routes={},
        auth=AUTH,
    )
    return checker.run()


def _results(out) -> dict[tuple[str, str, str], str]:
    return {(line["step"], line["kind"], line["actor"]): line["result"] for line in out["lines"] if line["scored"]}


def test_a_correct_app_meets_every_expectation(backend):
    backend()
    out = _check()
    assert set(_results(out).values()) == {"pass"}, _results(out)
    computed = score(out["lines"])
    assert computed["decidedPercent"] == 100 and computed["counts"]["fail"] == 0
    assert out["paths"][0]["completed"] is True
    line = next(line for line in out["lines"] if line["kind"] == "refused")
    assert line["evidence"]["status"] == 403 and line["evidence"]["as"] == "member", "every line carries its evidence"


def test_records_seen_by_others_and_actions_by_the_wrong_role_are_failures(backend):
    backend({"everyone_reads", "anyone_closes"})
    results = _results(_check())
    assert results[("ask", "hidden", "other:member")] == "fail", "another member reads a record that is not theirs"
    assert results[("close", "refused", "member")] == "fail", "a member closes"
    # the member's wrong close changed the record: the staff's own close is blocked by it, not a failure of its own
    assert results[("close", "does", "staff")] == "blocked"


def test_an_automatic_step_needs_no_call(backend):
    backend()
    binding = json.loads(json.dumps(BINDING))
    binding["steps"][1] |= {"automatic": True, "operationId": ""}
    expected = json.loads(json.dumps(EXPECTED))
    expected["paths"][0]["steps"][1]["statusAfter"] = "open"
    results = _results(_check(binding, expected))
    assert results[("close", "does", "staff")] == "pass"


def test_an_unbound_step_is_unknown_not_failed(backend):
    backend()
    binding = json.loads(json.dumps(BINDING))
    binding["steps"] = binding["steps"][:1]
    out = _check(binding)
    results = _results(out)
    assert results[("close", "does", "staff")] == "unbound"
    computed = score(out["lines"])
    assert computed["counts"]["unbound"] >= 1 and computed["decidedPercent"] == 100


class _Store:
    """Records what the evaluation writes; it has no generation methods at all (D4: it never touches one)."""

    def __init__(self):
        self.updates: list[dict[str, Any]] = []

    def evaluation(self, run_id):
        return SimpleNamespace(id=run_id, generation_id="gen_1", provider="fake", expectations_from=None)

    def update_evaluation(self, run_id, **fields):
        self.updates.append(fields)


def test_a_failing_evaluation_is_the_evaluations_own():
    store = _Store()
    service = EvaluationService(store, prompts=None)  # type: ignore[arg-type]

    async def broken(*args, **kwargs):
        raise RuntimeError("the backend preview is not running")

    service._evaluate = broken  # type: ignore[method-assign]
    asyncio.run(service.run(uuid.uuid4()))
    assert store.updates[0]["status"] == "RUNNING"
    assert store.updates[-1]["status"] == "FAILED" and "preview is not running" in store.updates[-1]["error"]


def test_the_evaluation_api_is_only_there_for_bound_workflows(client, user_headers, clean_redis):
    """Story 26.6: a generation whose draft has no bound workflows has nothing to evaluate (404, no Business tab; "Run"
    is 422); once bound, the API says no run yet (`NONE`) and "Run" queues one on the provider's queue."""
    from sqlmodel import Session

    from src.libs.database import db_session_manager
    from src.modules.shared.infrastructure.models import GenerationModel, SpecDraftModel

    res = client.post(
        "/api/v1/generations",
        json={
            "mode": "dynamic",
            "requirement": {"text": "A small library where members borrow books and staff record returns."},
            "options": {"engine": "fake", "llmProvider": "antigravity"},
        },
        headers=user_headers,
    )
    assert res.status_code == 202, res.text
    gen_id = res.json()["generationId"]
    url = f"/api/v1/generations/{gen_id}/evaluation"
    assert client.get(url, headers=user_headers).status_code == 404
    assert client.post(f"{url}/run", headers=user_headers).status_code == 422

    with Session(db_session_manager.engine) as session:
        draft_id = session.get(GenerationModel, gen_id).options["draftId"]
        draft = session.get(SpecDraftModel, uuid.UUID(draft_id))
        draft.business = {"business": BUSINESS, "expected": {}, "binding": {"steps": []}}
        session.add(draft)
        session.commit()

    res = client.get(url, headers=user_headers)
    assert res.status_code == 200 and res.json()["status"] == "NONE"
    res = client.post(f"{url}/run", headers=user_headers)
    assert res.status_code == 202 and res.json()["provider"] == "antigravity"
    assert client.get(url, headers=user_headers).json()["status"] == "PENDING"

    # Story 26.7: the same requirement without the business layer, checked against this generation's expectations
    res = client.post(
        "/api/v1/generations",
        json={
            "mode": "dynamic",
            "requirement": {"text": "A small library where members borrow books and staff record returns."},
            "options": {"engine": "fake", "llmProvider": "antigravity", "businessWorkflows": False},
        },
        headers=user_headers,
    )
    off = res.json()["generationId"]
    off_url = f"/api/v1/generations/{off}/evaluation"
    assert client.get(off_url, headers=user_headers).status_code == 404
    res = client.post(f"{off_url}/run", json={"expectationsFrom": off}, headers=user_headers)
    assert res.status_code == 422, "its own expectations: it has none"
    res = client.post(f"{off_url}/run", json={"expectationsFrom": gen_id}, headers=user_headers)
    assert res.status_code == 202 and res.json()["expectationsFrom"] == gen_id
    assert client.get(off_url, headers=user_headers).json()["expectationsFrom"] == gen_id, "now it has a tab"
    res = client.post(f"{off_url}/run", headers=user_headers)
    assert res.status_code == 202 and res.json()["expectationsFrom"] == gen_id, "Run again keeps the source"


def test_another_generations_expectations_are_bound_to_this_app_first(tmp_path):
    """Story 26.7: an app generated without the business layer is checked against the first run's frozen expectations;
    the workflows are bound to its own contract and screens (one binding call, its usage counted), never reused."""
    from fake_llm import FakeLlmProvider

    from src.engines import PromptLibrary

    asked: list[str] = []

    def bind(prompt, schema):
        asked.append(prompt)
        return {"actors": [], "records": [], "setup": [], "steps": [], "effects": [], "outcomes": [], "unbound": []}

    contract = {"paths": {"/books": {"get": {"operationId": "book.list", "responses": {"200": {}}}}}}
    generation = SimpleNamespace(spec_id="s", frontend_spec_id="f")
    store = SimpleNamespace(
        generation=lambda gid: generation,
        spec=lambda sid: SimpleNamespace(raw_json=json.dumps({"entities": []})),
        frontend_spec=lambda fid: SimpleNamespace(raw_json=json.dumps({"pages": [{"id": "books", "route": "/books"}]})),
    )
    service = EvaluationService(store, PromptLibrary())  # type: ignore[arg-type]
    calls: list[dict[str, Any]] = []
    binding = asyncio.run(
        service._bind_here(
            "gen_off", BUSINESS, {"paths": []}, contract, FakeLlmProvider({"bind_workflows": bind}), tmp_path, calls
        )
    )
    assert len(asked) == 1 and "book.list" in asked[0] and '"books"' in asked[0]
    assert [c["purpose"] for c in calls] == ["bind_workflows"]
    assert {"what": "step ask of handle", "reason": "the binding left this step out"} in binding["problems"]


def test_the_providers_scratch_dir_is_inside_the_workspace_root():
    """agy and claude run only inside WORKSPACE_ROOT (Epic 24); the evaluation's first real run failed with
    `WorkspaceViolation` when its scratch dir was under ARTIFACT_ROOT (the fake provider never checks)."""
    from pathlib import Path

    from src.configs import config
    from src.engines.workspace import ensure_inside
    from src.orchestrator.evaluation.service import evaluation_state_dir

    state = evaluation_state_dir(uuid.uuid4())
    ensure_inside(state, Path(config.workspace_root))
    assert not state.is_relative_to(Path(config.artifact_root).resolve())


def test_a_role_that_reads_through_its_own_operation_sees_the_record(backend):
    """HomeFix: the assigned contractor reads a request through `GET /repair-requests/jobs/{id}`, not the tenant's
    `GET /repair-requests/{id}` the binding names; the line passes through the role's own read (as its screens do)
    and the evidence names it. Without such a read it is still a failure."""
    backend({"staff_reads_at_desk"})
    expected = json.loads(json.dumps(EXPECTED))
    expected["paths"][0]["steps"][1]["visibleTo"] = ["staff"]
    fields = {"id": "string", "title": "string", "status": "enum OPEN|CLOSED"}
    with_desk = [{**op, "response": fields} if op["operationId"] == "request.get" else op for op in OPERATIONS] + [
        {"operationId": "request.atDesk", "method": "GET", "path": "/desk/{id}", "response": fields}
    ]

    def run(operations):
        checker = Checker(
            api=Api("http://localhost:9999", AUTH, operations), second_look=None, log=lambda line: None,
            business=BUSINESS, expected=expected, binding=BINDING, walker=None, frontend="", routes={}, auth=AUTH,
        )  # fmt: skip
        out = checker.run()
        return next(line for line in out["lines"] if line["kind"] == "visible" and line["actor"] == "staff")

    line = run(with_desk)
    assert line["result"] == "pass" and "/desk/" in line["evidence"]["call"], line
    # drafted without a response type (HomeFix's `getJob`): the same resource's untyped read counts too
    typed = [{**op, "response": fields} if op["operationId"] == "request.get" else op for op in OPERATIONS]
    same = typed + [{"operationId": "request.atDesk", "method": "GET", "path": "/requests/desk/{id}"}]
    line = run(same)
    assert line["result"] == "pass" and "/requests/desk/" in line["evidence"]["call"], line
    other = typed + [{"operationId": "desk.get", "method": "GET", "path": "/desk/{id}"}]
    assert run(other)["result"] == "fail", "an untyped read of another resource is not this record's"
    assert run(OPERATIONS)["result"] == "fail", "no other read: the staff cannot see it"


def test_the_screens_are_taken_on_the_live_api_never_the_mocks():
    """HomeFix (2026-11-08): a frontend preview started again runs on the mocks, where the records the checker created
    through the live API do not exist, so every record page was "Could not load this". The evaluation switches only the
    preview to the live API (`switch-frontend`, never the generation's integration: D4) and takes no screenshots when
    it does not get there."""
    from src.modules.shared.domain.enums import PreviewStatus

    backend = SimpleNamespace(url="http://localhost:18001", status=PreviewStatus.RUNNING, mock_api=None)

    def frontend(mock_api):
        return SimpleNamespace(url="http://localhost:18002", status=PreviewStatus.RUNNING, mock_api=mock_api)

    class Redis:
        def __init__(self):
            self.sent: list[dict[str, Any]] = []

        async def lpush(self, key, value):
            self.sent.append(json.loads(value))

    def service(rows):
        store = _Store()
        store.preview = lambda generation_id, kind: rows.pop(0) if len(rows) > 1 else rows[0]
        svc = EvaluationService(store, prompts=None, redis=Redis())  # type: ignore[arg-type]
        svc.switch_timeout_s = 1.0
        return svc

    live = frontend(False)
    svc = service([live])
    assert asyncio.run(svc._live_frontend(uuid.uuid4(), "gen_1", {"backend": backend, "frontend": live})) is live
    assert svc.redis.sent == [], "already on the live API: nothing to switch"

    switched = frontend(False)
    svc = service([frontend(True), switched])
    got = asyncio.run(svc._live_frontend(uuid.uuid4(), "gen_1", {"backend": backend, "frontend": frontend(True)}))
    assert got is switched
    args = {"kind": "frontend", "mockApi": False, "apiBaseUrl": "http://localhost:18001"}
    assert svc.redis.sent == [{"op": "switch-frontend", "generationId": "gen_1", "args": args}]

    svc = service([frontend(True)])
    assert (
        asyncio.run(svc._live_frontend(uuid.uuid4(), "gen_1", {"backend": backend, "frontend": frontend(True)})) is None
    )
