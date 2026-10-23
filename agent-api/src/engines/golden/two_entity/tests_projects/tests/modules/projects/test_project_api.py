import uuid

MISSING = str(uuid.uuid4())


def _create(client, name="Apollo", **extra):
    response = client.post("/projects", json={"name": name, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def test_create_project__ok(client):
    response = client.post("/projects", json={"name": "Apollo", "description": "Moon"})

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Apollo" and body["description"] == "Moon"
    assert uuid.UUID(body["id"]) and body["createdAt"]


def test_create_project__invalid(client):
    assert client.post("/projects", json={"description": "no name"}).status_code == 422
    response = client.post("/projects", json={"name": "x" * 121})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_project__conflict(client):
    _create(client, "Apollo")

    response = client.post("/projects", json={"name": "Apollo"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_get_project__ok(client):
    project = _create(client)

    response = client.get(f"/projects/{project['id']}")

    assert response.status_code == 200
    assert response.json() == project


def test_get_project__not_found(client):
    response = client.get(f"/projects/{MISSING}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_list_projects__ok(client):
    _create(client, "Apollo")
    _create(client, "Gemini")

    body = client.get("/projects").json()

    assert body["total"] == 2 and body["limit"] == 20 and body["offset"] == 0
    assert {item["name"] for item in body["items"]} == {"Apollo", "Gemini"}


def test_list_projects__pagination(client):
    for index in range(5):
        _create(client, f"P{index}")

    page = client.get("/projects", params={"limit": 2, "offset": 2, "sort": "name"}).json()

    assert page["total"] == 5
    assert [item["name"] for item in page["items"]] == ["P2", "P3"]


def test_list_projects__sort(client):
    for name in ("Gemini", "Apollo", "Mercury"):
        _create(client, name)

    ascending = client.get("/projects", params={"sort": "name"}).json()["items"]
    descending = client.get("/projects", params={"sort": "-name"}).json()["items"]

    assert [p["name"] for p in ascending] == ["Apollo", "Gemini", "Mercury"]
    assert [p["name"] for p in descending] == ["Mercury", "Gemini", "Apollo"]


def test_list_projects__invalid_sort(client):
    assert client.get("/projects", params={"sort": "description"}).status_code == 422


def test_update_project__ok(client):
    project = _create(client, "Apollo", description="Moon")

    response = client.patch(f"/projects/{project['id']}", json={"description": "Moon landing"})

    assert response.status_code == 200
    assert response.json()["description"] == "Moon landing"
    assert response.json()["name"] == "Apollo"


def test_update_project__not_found(client):
    assert client.patch(f"/projects/{MISSING}", json={"name": "x"}).status_code == 404


def test_update_project__invalid(client):
    project = _create(client)

    assert client.patch(f"/projects/{project['id']}", json={"name": ""}).status_code == 422


def test_delete_project__ok(client):
    project = _create(client)

    assert client.delete(f"/projects/{project['id']}").status_code == 204
    assert client.get(f"/projects/{project['id']}").status_code == 404


def test_delete_project__not_found(client):
    assert client.delete(f"/projects/{MISSING}").status_code == 404
