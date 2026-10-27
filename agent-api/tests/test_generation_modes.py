"""Generation modes, lanes and the FrontendSpec API (Stories 12.1, 12.2, 12.3, 12.5)."""

import json
from pathlib import Path

import pytest

from src.engines.fake_engine import FakeEngine, demo_scenario
from src.modules.shared.domain.enums import GenerationMode, GenerationStatus
from src.modules.shared.domain.generation_modes import close_lanes, overall_status
from src.orchestrator.contract import build_contract, dump_contract
from workflow_helpers import TWO_ENTITY, cli_invocations, events, generation, node_runs, run_job

EXAMPLES = Path(__file__).parents[2] / "examples"
SHOP = json.loads((EXAMPLES / "specs" / "shop.json").read_text())
SHOP_FRONTEND = json.loads((EXAMPLES / "frontend-specs" / "shop-dynamic.json").read_text())
TRACKER_FRONTEND = json.loads((EXAMPLES / "frontend-specs" / "project-tracker-dynamic.json").read_text())
LANDING = json.loads((EXAMPLES / "frontend-specs" / "static-landing.json").read_text())
OPTIONS = {"engine": "fake", "deployPreview": False}


@pytest.fixture
def headers(login):
    def _headers(email: str = "user@test.local", password: str = "userpass") -> dict:
        return {"Authorization": f"Bearer {login(email, password)}"}

    return _headers


# -- overall status ----------------------------------------------------------------------------------------------

B, S, D = GenerationMode.BACKEND, GenerationMode.STATIC, GenerationMode.DYNAMIC


@pytest.mark.parametrize(
    ("mode", "lanes", "expected"),
    [
        (B, {"backend": "COMPLETED"}, "COMPLETED"),
        (B, {"backend": "FAILED"}, "FAILED"),
        (S, {"frontend": "COMPLETED"}, "COMPLETED"),
        (S, {"frontend": "SKIPPED"}, "COMPLETED_WITH_WARNINGS"),
        (D, {"backend": "COMPLETED", "frontend": "COMPLETED", "integration": "COMPLETED"}, "COMPLETED"),
        (D, {"backend": "FAILED", "frontend": "COMPLETED", "integration": "SKIPPED"}, "COMPLETED_WITH_WARNINGS"),
        (D, {"backend": "COMPLETED", "frontend": "FAILED", "integration": "SKIPPED"}, "FAILED"),
        (D, {"backend": "COMPLETED", "frontend": "SKIPPED", "integration": "SKIPPED"}, "COMPLETED_WITH_WARNINGS"),
        (D, {"backend": "FAILED", "frontend": "SKIPPED", "integration": "SKIPPED"}, "FAILED"),
    ],
)
def test_overall_status_follows_the_lane_rules(mode, lanes, expected):
    assert overall_status(mode, lanes) == GenerationStatus(expected)


def test_close_lanes_fails_the_active_lane_and_skips_the_rest():
    lanes = {"backend": "REPAIRING", "frontend": "PENDING", "integration": "SKIPPED"}
    assert close_lanes(lanes, failed=True) == {"backend": "FAILED", "frontend": "SKIPPED", "integration": "SKIPPED"}
    assert close_lanes(lanes, failed=False)["backend"] == "SKIPPED"


# -- FrontendSpec API --------------------------------------------------------------------------------------------


def _post_json(client, url: str, body, headers: dict):
    return client.post(url, content=json.dumps(body), headers={**headers, "content-type": "application/json"})


def test_frontend_spec_routes_require_auth(client):
    assert client.get("/api/v1/frontend-specs/schema").status_code == 401
    assert client.post("/api/v1/frontend-specs/validate", content=b"{}").status_code == 401


def test_frontend_spec_schema_and_validation(client, headers):
    schema = client.get("/api/v1/frontend-specs/schema", headers=headers())
    assert schema.status_code == 200 and schema.json()["title"] == "FrontendSpec 1.0"
    assert client.get("/api/v1/frontend-specs/schema?version=2.0", headers=headers()).status_code == 404

    ok = _post_json(client, "/api/v1/frontend-specs/validate", LANDING, headers()).json()
    assert ok == {"valid": True, "specVersion": "1.0", "errors": [], "warnings": []}
    broken = {**LANDING, "layout": {"header": {"navigation": [{"label": "X", "page": "nowhere"}]}}}
    report = _post_json(client, "/api/v1/frontend-specs/validate", broken, headers()).json()
    assert not report["valid"] and report["errors"][0]["code"] == "FE_UNKNOWN_PAGE"


def test_validate_against_a_backend_spec_runs_the_consistency_check(client, headers):
    backend_id = _post_json(client, "/api/v1/specs", TWO_ENTITY, headers()).json()["specId"]
    url = f"/api/v1/frontend-specs/validate?backendSpecId={backend_id}"

    assert _post_json(client, url, TRACKER_FRONTEND, headers()).json()["valid"] is True
    report = _post_json(client, url, SHOP_FRONTEND, headers()).json()
    assert not report["valid"]
    first = report["errors"][0]
    assert first["code"] == "CONTRACT_UNKNOWN_OPERATION"
    assert first["path"] == "/pages/0/sections/1/data/operationId" and first["backendPath"] == "/operations"

    static = _post_json(client, url, LANDING, headers()).json()
    assert static["valid"] and static["warnings"][0]["code"] == "FE_UNSUPPORTED_FEATURE"
    other = _post_json(client, url, TRACKER_FRONTEND, headers("other@test.local", "otherpass"))
    assert other.status_code == 404


def test_frontend_specs_are_stored_and_owner_scoped(client, headers):
    created = _post_json(client, "/api/v1/frontend-specs", SHOP_FRONTEND, headers())
    assert created.status_code == 201, created.text
    spec_id = created.json()["specId"]
    fetched = client.get(f"/api/v1/frontend-specs/{spec_id}", headers=headers()).json()
    assert fetched["mode"] == "dynamic" and json.loads(fetched["raw"]) == SHOP_FRONTEND
    assert fetched["normalized"]["pages"][0]["id"] == "home"
    assert (
        client.get(f"/api/v1/frontend-specs/{spec_id}", headers=headers("other@test.local", "otherpass")).status_code
        == 404
    )
    assert (
        client.get(f"/api/v1/frontend-specs/{spec_id}", headers=headers("admin@test.local", "adminpass")).status_code
        == 200
    )

    invalid = _post_json(client, "/api/v1/frontend-specs", {**LANDING, "pages": []}, headers())
    assert invalid.status_code == 422 and invalid.json()["error"]["code"] == "SPEC_INVALID"


# -- creating generations ----------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        {"mode": "static", "backendSpec": TWO_ENTITY},
        {"mode": "static"},
        {"mode": "dynamic", "frontendSpec": TRACKER_FRONTEND},
        {"mode": "dynamic", "backendSpec": TWO_ENTITY},
        {"mode": "backend", "backendSpec": TWO_ENTITY, "frontendSpec": TRACKER_FRONTEND},
        {"mode": "static", "frontendSpec": TRACKER_FRONTEND},  # a dynamic FrontendSpec
        {"mode": "dynamic", "frontendSpec": LANDING, "backendSpec": TWO_ENTITY},  # a static FrontendSpec
    ],
)
def test_inputs_must_match_the_mode(client, headers, body):
    response = client.post("/api/v1/generations", json={**body, "options": OPTIONS}, headers=headers())
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "MODE_INPUT_MISMATCH"


def test_a_stored_frontend_spec_must_match_the_mode(client, headers):
    spec_id = _post_json(client, "/api/v1/frontend-specs", TRACKER_FRONTEND, headers()).json()["specId"]
    body = {"mode": "static", "frontendSpecId": spec_id, "options": OPTIONS}
    response = client.post("/api/v1/generations", json=body, headers=headers())
    assert response.status_code == 422 and response.json()["error"]["code"] == "MODE_INPUT_MISMATCH"


def _submit(client, headers: dict, body: dict) -> str:
    response = client.post("/api/v1/generations", json={**body, "options": OPTIONS}, headers=headers)
    assert response.status_code == 202, response.text
    return response.json()["generationId"]


def test_generations_carry_mode_lanes_and_frontend_options(client, headers):
    generation_id = _submit(client, headers(), {"mode": "static", "frontendSpec": LANDING})
    detail = client.get(f"/api/v1/generations/{generation_id}", headers=headers()).json()
    assert detail["mode"] == "static" and detail["specId"] is None and detail["frontendSpecId"]
    assert detail["lanes"] == {"frontend": "PENDING"}
    assert detail["projectName"] == "Northwind Studio"
    assert detail["options"]["frontend"] == {"runTests": True, "generatePreview": True, "mockApi": True}
    listed = client.get("/api/v1/generations", headers=headers()).json()["items"]
    row = next(item for item in listed if item["generationId"] == generation_id)
    assert (
        row["mode"] == "static" and row["lanes"] == {"frontend": "PENDING"} and row["projectName"] == "Northwind Studio"
    )

    backend_id = _submit(client, headers(), {"backendSpec": TWO_ENTITY})
    backend = client.get(f"/api/v1/generations/{backend_id}", headers=headers()).json()
    assert backend["mode"] == "backend" and backend["lanes"] == {"backend": "PENDING"}
    assert "frontend" not in backend["options"]


def test_workflow_graph_per_mode(client, headers):
    backend = client.get("/api/v1/generations/graph", headers=headers()).json()
    dynamic = client.get("/api/v1/generations/graph?mode=dynamic", headers=headers()).json()
    static = client.get("/api/v1/generations/graph?mode=static", headers=headers()).json()
    ids = {
        name: [node["id"] for node in graph["nodes"]] for name, graph in (("b", backend), ("d", dynamic), ("s", static))
    }
    assert "validate_spec" in ids["b"] and "validate_inputs" not in ids["b"]
    assert ids["d"][:3] == ["__start__", "validate_inputs", "build_contract"] and "validate_spec" not in ids["d"]
    assert ids["s"] == ["__start__", "validate_inputs", "package_artifacts", "__end__"]
    lanes = {node["id"]: node["lane"] for node in dynamic["nodes"] if not node["id"].startswith("__")}
    assert lanes["generate_backend"] == "backend" and lanes["build_contract"] is None


# -- running them ------------------------------------------------------------------------------------------------


def _artifacts(client, headers: dict, generation_id: str) -> dict[str, dict]:
    items = client.get(f"/api/v1/generations/{generation_id}/artifacts", headers=headers).json()["items"]
    return {item["name"]: item for item in items}


def test_dynamic_generation_builds_the_contract_then_the_backend_lane(client, headers, tmp_path):
    generation_id = _submit(
        client, headers(), {"mode": "dynamic", "frontendSpec": TRACKER_FRONTEND, "backendSpec": TWO_ENTITY}
    )
    assert run_job(tmp_path, generation_id, engine=FakeEngine(tmp_path, demo_scenario(0))) == "COMPLETED_WITH_WARNINGS"

    row = generation(generation_id)
    assert row.lanes == {"backend": "COMPLETED", "frontend": "SKIPPED", "integration": "SKIPPED"}
    assert "Epic 13" in row.error_summary
    nodes = [run.node for run in node_runs(generation_id)]
    assert nodes[:3] == ["validate_inputs", "build_contract", "plan_architecture"] and "validate_spec" not in nodes

    artifacts = _artifacts(client, headers(), generation_id)
    assert {"contract.json", "frontend-spec.json", "spec.json", "backend.zip", "manifest.json"} <= set(artifacts)
    assert artifacts["contract.json"]["kind"] == "contract"
    url = f"/api/v1/generations/{generation_id}/artifacts/{artifacts['contract.json']['artifactId']}"
    contract_text = client.get(url, headers=headers()).text
    from generation_helpers import normalized

    assert contract_text == dump_contract(build_contract(normalized(EXAMPLES / "specs" / "two-entity.json")))
    project = tmp_path / generation_id / "project"
    assert (project / ".bga" / "contract.json").read_text() == contract_text
    manifest = json.loads(
        client.get(
            f"/api/v1/generations/{generation_id}/artifacts/{artifacts['manifest.json']['artifactId']}",
            headers=headers(),
        ).text
    )
    assert manifest["artifacts"]["contract"] == artifacts["contract.json"]["artifactId"]

    stored = events(generation_id)
    lane_changes = [(e.lane, e.status) for e in stored if e.type == "lane.changed"]
    assert ("frontend", "SKIPPED") in lane_changes and ("backend", "COMPLETED") in lane_changes
    assert {e.lane for e in stored if e.step == "generate_backend"} == {"backend"}
    assert {e.lane for e in stored if e.step == "build_contract"} == {None}
    ready = next(e for e in stored if e.type == "contract.ready")
    assert ready.payload["operations"] == 10 and len(ready.payload["sha256"]) == 64
    assert stored[-1].type == "status.changed" and stored[-1].status == "COMPLETED_WITH_WARNINGS"
    assert stored[-1].payload["errorCode"] == "LANES_INCOMPLETE"


def test_dynamic_generation_with_inconsistent_specs_fails_before_any_engine_call(client, headers, tmp_path):
    generation_id = _submit(
        client, headers(), {"mode": "dynamic", "frontendSpec": SHOP_FRONTEND, "backendSpec": TWO_ENTITY}
    )
    assert run_job(tmp_path, generation_id) == "FAILED"
    row = generation(generation_id)
    assert row.lanes == {"backend": "SKIPPED", "frontend": "SKIPPED", "integration": "SKIPPED"}
    assert cli_invocations(generation_id) == []
    invalid = next(e for e in events(generation_id) if e.type == "spec.invalid")
    assert invalid.payload["total"] == 6
    assert {error["spec"] for error in invalid.payload["errors"]} == {"consistency"}
    assert invalid.payload["errors"][0]["backendPath"] == "/operations"
    assert row.error_summary.startswith("6 input error(s); first: consistency /pages/0/sections/1/data/operationId")


def test_static_generation_validates_and_packages_the_frontend_spec(client, headers, tmp_path):
    deployed = []

    async def on_completed(generation_id):
        deployed.append(generation_id)

    generation_id = _submit(client, headers(), {"mode": "static", "frontendSpec": LANDING})
    assert run_job(tmp_path, generation_id, on_completed=on_completed) == "COMPLETED_WITH_WARNINGS"
    row = generation(generation_id)
    assert row.lanes == {"frontend": "SKIPPED"} and "Frontend generation is not available yet" in row.error_summary
    assert [run.node for run in node_runs(generation_id)] == ["validate_inputs", "package_artifacts"]
    assert cli_invocations(generation_id) == [] and deployed == []
    artifacts = _artifacts(client, headers(), generation_id)
    assert set(artifacts) == {"frontend-spec.json", "report.json", "report.md"}
    report = client.get(
        f"/api/v1/generations/{generation_id}/artifacts/{artifacts['report.json']['artifactId']}", headers=headers()
    ).json()
    assert report["outcome"] == "COMPLETED_WITH_WARNINGS"
    preview = client.post(f"/api/v1/generations/{generation_id}/preview/start", headers=headers())
    assert preview.status_code in (409, 404)


def test_backend_generation_is_unchanged(client, headers, tmp_path):
    generation_id = _submit(client, headers(), {"backendSpec": TWO_ENTITY})
    assert run_job(tmp_path, generation_id, engine=FakeEngine(tmp_path, demo_scenario(0))) == "COMPLETED"
    row = generation(generation_id)
    assert row.mode == "backend" and row.lanes == {"backend": "COMPLETED"} and row.error_summary is None
    assert "contract.json" not in _artifacts(client, headers(), generation_id)
    assert node_runs(generation_id)[0].node == "validate_spec"
