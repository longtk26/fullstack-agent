import json
from pathlib import Path

import pytest

from src.modules.shared.domain.frontend_site import FrontendImportError, import_frontend_site

SITE_FILE = Path(__file__).parents[2] / "examples" / "frontend" / "revue-de-mode.json"
SNAPSHOT = Path(__file__).parent / "fixtures" / "frontend" / "revue-de-mode.expected.json"


@pytest.fixture(scope="module")
def site():
    return json.loads(SITE_FILE.read_text())


def test_matches_reviewed_snapshot(site):
    result = import_frontend_site(site).model_dump(mode="json")

    assert result == json.loads(SNAPSHOT.read_text())


def test_fixture_import_is_a_valid_spec_matching_the_page_bindings(site):
    result = import_frontend_site(site)
    spec = result.backend_spec
    ops = {op["operationId"]: op for op in spec["operations"]}

    assert result.validation.valid
    assert result.unresolved == []
    assert [e["name"] for e in spec["entities"]] == ["Post"]
    assert ops["post.list"]["pagination"]["defaultLimit"] == 8
    assert ops["post.list"]["sort"] == ["date", "title", "category"]
    assert ops["post.list"]["search"] == ["title", "excerpt", "author", "category"]
    assert ops["post.list"]["filters"] == ["category"]
    assert ops["post.listRelated"]["path"] == "/posts/{id}/related"
    assert len(result.seed[0]["records"]) == 8
    assert {b["operationId"] for b in result.bindings} == {"post.list", "post.get", "post.listRelated"}


def test_string_ids_become_a_string_primary_key(site):
    fields = import_frontend_site(site).backend_spec["entities"][0]["fields"]

    assert fields[0] == {"name": "id", "type": "string", "primary": True, "maxLength": 64}


def test_admin_crud_can_be_turned_off(site):
    result = import_frontend_site(site, include_admin_crud=False)

    assert [op["operationId"] for op in result.backend_spec["operations"]] == [
        "post.list",
        "post.get",
        "post.listRelated",
    ]
    assert result.validation.valid


def test_binding_params_drop_presentation_props(site):
    params = [b["params"] for b in import_frontend_site(site).bindings]

    assert not any("className" in p for p in params)


def test_records_without_ids_get_a_generated_uuid_key():
    site = {"name": "Shop", "collections": [{"key": "products", "records": [{"name": "Hat", "price": 9.5}]}]}

    result = import_frontend_site(site)

    fields = result.backend_spec["entities"][0]["fields"]
    assert fields[0] == {"name": "id", "type": "uuid", "primary": True}
    assert {"name": "price", "type": "float", "required": True} in fields
    assert result.validation.valid


def test_ambiguous_collection_and_unknown_components_are_unresolved():
    site = {
        "collections": [{"key": "posts", "records": [{"id": "a"}]}, {"key": "authors", "records": [{"id": "b"}]}],
        "pages": [
            {
                "slug": "home",
                "tree": {"type": "main", "children": [{"type": "CollectionBrowser"}, {"type": "RecordCarousel"}]},
            }
        ],
    }

    result = import_frontend_site(site)

    messages = [note.message for note in result.unresolved]
    assert any("does not say which collection" in m for m in messages)
    assert any("Unknown data component 'RecordCarousel'" in m for m in messages)
    assert result.validation.valid


def test_explicit_collection_prop_selects_the_collection():
    site = {
        "collections": [{"key": "posts", "records": [{"id": "a"}]}, {"key": "authors", "records": [{"id": "b"}]}],
        "pages": [{"slug": "team", "tree": {"type": "CollectionDetail", "props": {"collection": "authors"}}}],
    }

    bindings = import_frontend_site(site).bindings

    assert bindings == [
        {
            "page": "team",
            "componentPath": "/pages/0/tree",
            "component": "CollectionDetail",
            "operationId": "author.get",
            "params": {},
        }
    ]


@pytest.mark.parametrize("site", [[], {"collections": "posts"}, {"collections": [], "pages": {}}])
def test_rejects_non_site_documents(site):
    with pytest.raises(FrontendImportError):
        import_frontend_site(site)


def test_import_endpoint(client, login):
    headers = {"Authorization": f"Bearer {login('user@test.local', 'userpass')}", "content-type": "application/json"}

    ok = client.post(
        "/api/v1/spec-imports/frontend?includeAdminCrud=false", content=SITE_FILE.read_bytes(), headers=headers
    )
    bad = client.post("/api/v1/spec-imports/frontend", content=b"[]", headers=headers)
    malformed = client.post("/api/v1/spec-imports/frontend", content=b"{", headers=headers)

    assert ok.status_code == 200
    assert ok.json()["validation"]["valid"] is True
    assert ok.json()["backendSpec"]["x-frontendBindings"][0]["operationId"] == "post.list"
    assert len(ok.json()["backendSpec"]["operations"]) == 3
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "FRONTEND_JSON_INVALID"
    assert malformed.status_code == 400 and malformed.json()["error"]["code"] == "JSON_MALFORMED"


def test_imported_spec_can_be_saved_as_a_spec(client, login):
    headers = {"Authorization": f"Bearer {login('user@test.local', 'userpass')}", "content-type": "application/json"}
    spec = client.post("/api/v1/spec-imports/frontend", content=SITE_FILE.read_bytes(), headers=headers).json()

    created = client.post("/api/v1/specs?source=frontend", content=json.dumps(spec["backendSpec"]), headers=headers)

    assert created.status_code == 201
