import json
from pathlib import Path

from scripts.export_spec_schema import render

SCHEMA_FILE = Path(__file__).parents[1] / "schemas" / "backend-spec-1.0.json"


def test_committed_schema_matches_models():
    assert SCHEMA_FILE.read_text() == render("1.0"), "run `make schema` and commit the result"


def test_schema_endpoint_serves_the_same_schema(client, login):
    token = login("user@test.local", "userpass")

    response = client.get("/api/v1/specs/schema", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == json.loads(SCHEMA_FILE.read_text())


def test_schema_endpoint_rejects_unknown_version(client, login):
    token = login("user@test.local", "userpass")

    response = client.get("/api/v1/specs/schema?version=9.9", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 404
