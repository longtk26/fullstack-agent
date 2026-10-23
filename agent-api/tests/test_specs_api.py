import json
from pathlib import Path

import pytest

TWO_ENTITY = (Path(__file__).parents[2] / "examples" / "specs" / "two-entity.json").read_bytes()
JSON_HEADERS = {"content-type": "application/json"}


@pytest.fixture
def auth(login):
    def _auth(email: str = "user@test.local", password: str = "userpass") -> dict:
        return {"Authorization": f"Bearer {login(email, password)}", **JSON_HEADERS}

    return _auth


def test_spec_routes_require_auth(client):
    assert client.post("/api/v1/specs/validate", content=TWO_ENTITY, headers=JSON_HEADERS).status_code == 401
    assert client.post("/api/v1/specs", content=TWO_ENTITY, headers=JSON_HEADERS).status_code == 401


def test_validate_returns_report_without_persisting(client, auth):
    response = client.post("/api/v1/specs/validate", content=TWO_ENTITY, headers=auth())

    assert response.status_code == 200
    assert response.json() == {"valid": True, "specVersion": "1.0", "errors": [], "warnings": []}


def test_validate_reports_malformed_json_as_a_200_report(client, auth):
    response = client.post("/api/v1/specs/validate", content=b'{"specVersion": ', headers=auth())

    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert response.json()["errors"][0]["code"] == "JSON_MALFORMED"


def test_create_stores_the_raw_spec_byte_for_byte(client, auth):
    raw = TWO_ENTITY.replace(b'"Project Tracker"', b'"Project   Tracker"')
    headers = auth()

    created = client.post("/api/v1/specs", content=raw, headers=headers)
    spec_id = created.json()["specId"]
    fetched = client.get(f"/api/v1/specs/{spec_id}", headers=headers)

    assert created.status_code == 201
    assert fetched.status_code == 200
    assert fetched.json()["raw"].encode() == raw
    assert fetched.json()["normalized"]["project"]["slug"] == "project-tracker"
    assert fetched.json()["source"] == "json"


def test_create_rejects_invalid_spec_with_issue_details(client, auth):
    spec = json.loads(TWO_ENTITY)
    spec["operations"][0]["method"] = "GET"

    response = client.post("/api/v1/specs", content=json.dumps(spec), headers=auth())

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "SPEC_INVALID"
    assert error["details"][0]["code"] == "METHOD_ACTION_MISMATCH"
    assert error["details"][0]["path"] == "/operations/0/method"


def test_other_users_spec_is_not_found_but_admin_can_read_it(client, auth):
    spec_id = client.post("/api/v1/specs", content=TWO_ENTITY, headers=auth()).json()["specId"]

    other = client.get(f"/api/v1/specs/{spec_id}", headers=auth("other@test.local", "otherpass"))
    admin = client.get(f"/api/v1/specs/{spec_id}", headers=auth("admin@test.local", "adminpass"))

    assert other.status_code == 404
    assert other.json()["error"]["code"] == "NOT_FOUND"
    assert admin.status_code == 200


def test_unknown_spec_is_not_found(client, auth):
    response = client.get("/api/v1/specs/00000000-0000-0000-0000-000000000000", headers=auth())

    assert response.status_code == 404


def test_oversized_body_is_rejected(client, auth):
    padding = b" " * 1_000_001

    response = client.post("/api/v1/specs/validate", content=TWO_ENTITY + padding, headers=auth())

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
