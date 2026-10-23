import uuid

MISSING = str(uuid.uuid4())


def _project(client, name="Apollo"):
    response = client.post("/projects", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _task(client, project_id, title="Launch", **extra):
    response = client.post("/tasks", json={"projectId": project_id, "title": title, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def test_create_task__ok(client):
    project_id = _project(client)

    response = client.post("/tasks", json={"projectId": project_id, "title": "Launch", "dueDate": "2026-12-01"})

    assert response.status_code == 201
    body = response.json()
    assert body["projectId"] == project_id and body["title"] == "Launch"
    assert body["status"] == "TODO" and body["priority"] == 3 and body["dueDate"] == "2026-12-01"


def test_create_task__invalid(client):
    project_id = _project(client)

    assert client.post("/tasks", json={"projectId": project_id}).status_code == 422
    assert client.post("/tasks", json={"projectId": project_id, "title": "x", "priority": 9}).status_code == 422
    assert client.post("/tasks", json={"projectId": project_id, "title": "x", "status": "LATE"}).status_code == 422


def test_create_task__bad_reference(client):
    response = client.post("/tasks", json={"projectId": MISSING, "title": "Orphan"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "REFERENCE_NOT_FOUND"


def test_get_task__ok(client):
    task = _task(client, _project(client))

    response = client.get(f"/tasks/{task['id']}")

    assert response.status_code == 200
    assert response.json() == task


def test_get_task__not_found(client):
    response = client.get(f"/tasks/{MISSING}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_list_tasks__ok(client):
    project_id = _project(client)
    _task(client, project_id, "A")
    _task(client, project_id, "B")

    body = client.get("/tasks").json()

    assert body["total"] == 2 and body["limit"] == 20 and body["offset"] == 0
    assert {item["title"] for item in body["items"]} == {"A", "B"}


def test_list_tasks__pagination(client):
    project_id = _project(client)
    for priority in (1, 2, 3, 4, 5):
        _task(client, project_id, f"T{priority}", priority=priority)

    page = client.get("/tasks", params={"limit": 2, "offset": 1, "sort": "priority"}).json()

    assert page["total"] == 5
    assert [item["priority"] for item in page["items"]] == [2, 3]


def test_list_tasks__filter_project_id(client):
    first, second = _project(client, "Apollo"), _project(client, "Gemini")
    _task(client, first, "A")
    _task(client, second, "B")

    body = client.get("/tasks", params={"projectId": first}).json()

    assert body["total"] == 1 and body["items"][0]["title"] == "A"


def test_list_tasks__filter_status(client):
    project_id = _project(client)
    _task(client, project_id, "A", status="DONE")
    _task(client, project_id, "B")

    body = client.get("/tasks", params={"status": "DONE"}).json()

    assert [item["title"] for item in body["items"]] == ["A"]


def test_list_tasks__sort(client):
    project_id = _project(client)
    _task(client, project_id, "late", dueDate="2026-12-31")
    _task(client, project_id, "early", dueDate="2026-01-01")

    ascending = client.get("/tasks", params={"sort": "dueDate"}).json()["items"]
    descending = client.get("/tasks", params={"sort": "-dueDate"}).json()["items"]

    assert [t["title"] for t in ascending] == ["early", "late"]
    assert [t["title"] for t in descending] == ["late", "early"]


def test_list_tasks__invalid_sort(client):
    assert client.get("/tasks", params={"sort": "title"}).status_code == 422


def test_update_task__ok(client):
    task = _task(client, _project(client))

    response = client.patch(f"/tasks/{task['id']}", json={"status": "IN_PROGRESS"})

    assert response.status_code == 200
    assert response.json()["status"] == "IN_PROGRESS" and response.json()["title"] == task["title"]


def test_update_task__not_found(client):
    assert client.patch(f"/tasks/{MISSING}", json={"title": "x"}).status_code == 404


def test_update_task__invalid(client):
    task = _task(client, _project(client))

    assert client.patch(f"/tasks/{task['id']}", json={"priority": "high"}).status_code == 422


def test_delete_task__ok(client):
    task = _task(client, _project(client))

    assert client.delete(f"/tasks/{task['id']}").status_code == 204
    assert client.get(f"/tasks/{task['id']}").status_code == 404


def test_delete_task__not_found(client):
    assert client.delete(f"/tasks/{MISSING}").status_code == 404
