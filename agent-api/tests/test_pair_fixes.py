"""Pair fixes: the BackendSpec follows what the pages need, and what it cannot provide is cut from the pages, so a
dynamic draft never stops for the user to fix the pair."""

import copy
import json

from generation_helpers import EXAMPLES
from test_drafting import _create, _run

from src.engines.fake_engine import FakeEngine, FakeStep
from src.orchestrator.pair_fixes import adapt_backend, pair_errors, prune_frontend

FRONTEND = json.loads((EXAMPLES / "frontend-specs" / "project-tracker-dynamic.json").read_text())
BACKEND = json.loads((EXAMPLES / "specs" / "two-entity.json").read_text())
IMPORT = {"operationId": "task.import", "type": "custom", "method": "POST", "path": "/tasks/import"}
SUMMARY = {
    "operationId": "project.summary",
    "type": "custom",
    "method": "GET",
    "path": "/projects/summary",
    "description": "For each project: projectName, openTasks and doneTasks (counted from its tasks).",
}


def _pair():
    frontend, backend = copy.deepcopy(FRONTEND), copy.deepcopy(BACKEND)
    backend["operations"] += [copy.deepcopy(IMPORT), copy.deepcopy(SUMMARY)]
    frontend["forms"].append(
        {
            "id": "importTasks",
            "operationId": "task.import",
            "fields": [
                {"name": "title", "label": "Title", "required": True},
                {"name": "dueDate", "type": "date", "label": "Due"},
                {"name": "source", "label": "Source"},
            ],
            "submitLabel": "Import",
            "onSuccess": {"toast": "Imported"},
        }
    )
    tasks = frontend["pages"][4]["sections"]
    tasks.append({"id": "import", "component": "Form", "form": "importTasks"})
    tasks.append({"id": "summary", "component": "CardGrid", "content": {}, "data": {"operationId": "project.summary"}})
    return frontend, backend


def _op(backend, operation_id):
    return next(op for op in backend["operations"] if op["operationId"] == operation_id)


def test_a_custom_operation_takes_what_its_form_sends_and_returns_what_its_page_reads():
    frontend, backend = _pair()
    assert len(pair_errors(frontend, backend)) >= 4
    adapted, notes = adapt_backend(frontend, backend)
    assert backend["operations"][-1] == SUMMARY, "works on a copy"
    request = _op(adapted, "task.import")["request"]["properties"]
    assert request == [
        {"name": "title", "type": "string", "required": True},
        {"name": "dueDate", "type": "date"},
        {"name": "source", "type": "string"},
    ], "types come from the entity field of that name, else from the form"
    response = _op(adapted, "project.summary")["response"]
    assert response["type"] == "array"
    assert [(p["name"], p["type"]) for p in response["properties"]] == [
        ("projectName", "string"),
        ("openTasks", "string"),
        ("doneTasks", "string"),
    ], "a list that names no fields takes them from the operation's description"
    assert all(note["spec"] == "backend" for note in notes)
    assert "'task.import' takes 'title', which its form sends" in [n["message"] for n in notes]
    assert pair_errors(frontend, adapted) == []


def test_a_list_gets_the_filter_and_sort_its_page_asks_for():
    frontend, backend = copy.deepcopy(FRONTEND), copy.deepcopy(BACKEND)
    table = frontend["pages"][4]["sections"][0]
    table["data"]["params"]["priority"] = 1
    table.setdefault("content", {})["controls"] = {"sort": ["title"]}
    adapted, notes = adapt_backend(frontend, backend)
    task_list = _op(adapted, "task.list")
    assert "priority" in task_list["filters"] and "title" in task_list["sort"]
    assert pair_errors(frontend, adapted) == [], [n["message"] for n in notes]


def test_what_the_backend_cannot_provide_is_cut_from_the_pages():
    frontend, backend = copy.deepcopy(FRONTEND), copy.deepcopy(BACKEND)
    frontend["pages"][4]["sections"][0]["data"]["params"]["lowStock"] = True  # no such field
    frontend["pages"][1]["sections"][0]["data"]["fields"].append("budgetLeft")  # CRUD: never invented
    adapted, adapt_notes = adapt_backend(frontend, backend)
    assert adapt_notes == [] and adapted == backend
    pruned, notes = prune_frontend(frontend, adapted)
    assert "lowStock" not in pruned["pages"][4]["sections"][0]["data"]["params"]
    assert pruned["pages"][1]["sections"][0]["data"]["fields"] == ["name", "createdAt"]
    assert pair_errors(pruned, adapted) == []
    messages = [n["message"] for n in notes]
    assert any(m.startswith("Parameter 'lowStock' removed") for m in messages), messages
    assert any(m.startswith("Field 'budgetLeft' removed") for m in messages), messages


def test_a_dynamic_draft_never_stops_on_the_pair(client, user_headers, tmp_path):
    frontend, backend = _pair()
    frontend["pages"][4]["sections"][0]["data"]["params"]["lowStock"] = True
    # Every call (the draft and each repair) writes the same pair: the repairs never fix it.
    step = FakeStep(
        write={
            "frontend-spec.json": json.dumps(frontend),
            "backend-spec.json": json.dumps(backend),
            "notes.json": "{}",
        }
    )
    draft_id = _create(client, user_headers, "dynamic", "A tracker for projects and their tasks.")
    draft = _run(tmp_path, draft_id, FakeEngine(tmp_path, {"*": [step]}))
    assert draft["status"] == "SUCCEEDED", draft["validation"]
    assert draft["validation"]["pair"]["valid"] is True and draft["error"] is None
    assert _op(draft["backend_spec"], "task.import")["request"]["properties"][0]["name"] == "title"
    messages = [n["message"] for n in draft["assumptions"]]
    assert any("Parameter 'lowStock' removed" in m for m in messages), messages
    assert any("'project.summary' returns a list" in m for m in messages), messages
