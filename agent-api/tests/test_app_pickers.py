"""Reference pickers and readable references (Story 22.6): an app form never asks for an id. What the server or the
signed-in user sets is not shown, a parent the page knows comes from the route, any other parent is picked by its name
from the parent's list (which code adds when the BackendSpec has none), and lists and details show parents by name.
Agent tests, no Node (decision FE-TESTS)."""

import json
import sys
from pathlib import Path

import pytest

from src.modules.shared.domain.backend_spec import validate_spec_data
from src.modules.shared.domain.frontend_spec import validate_frontend_spec_data
from src.modules.shared.domain.frontend_spec.registry import frontend_spec_json_schema
from src.orchestrator.backend.planner import build_plan
from src.orchestrator.checks.consistency import check_spec_pair
from src.orchestrator.frontend.app.screens import ensure_aggregates
from src.orchestrator.integration.contract import build_contract

sys.path.insert(0, str(Path(__file__).parent))
from test_app_screens import APPS, _example, _plan  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "app-forms"
KIT = Path(__file__).parents[1] / "templates/nextjs_overlay/files/dynamic/app/src/components/app"
OVERLAY = Path(__file__).parents[1] / "templates/nextjs_overlay/files/dynamic"


def _apps() -> dict[str, tuple[dict, object]]:
    out = {}
    for name in sorted(APPS):
        backend, raw = _example(name)
        backend, _, _, screens = _plan(backend, raw)
        out[name] = (backend, screens)
    backend = validate_spec_data(json.loads((FIXTURE / "backend.json").read_text())).normalized
    backend, _, _, screens = _plan(backend, json.loads((FIXTURE / "outline.json").read_text()))
    out["venue-bookings"] = (backend, screens)
    return out


APPS_WITH_FIXTURE = _apps()


def _request_sources(contract: dict, op_id: str) -> dict[str, str]:
    from src.orchestrator.integration.contract import contract_operations, resolve

    operation = contract_operations(contract)[op_id]["operation"]
    schema = resolve(contract, operation["requestBody"]["content"]["application/json"]["schema"])
    return {name: (prop.get("x-bga") or {}).get("source") for name, prop in (schema.get("properties") or {}).items()}


@pytest.mark.parametrize("name", sorted(APPS_WITH_FIXTURE))
def test_no_app_form_shows_an_id_input(name):
    backend, screens = APPS_WITH_FIXTURE[name]
    contract = build_contract(backend, build_plan(backend))
    for form in screens.spec["forms"]:
        sources = _request_sources(contract, form["operationId"])
        for field in form["fields"]:
            if sources.get(field["name"]) == "reference":
                assert field.get("hidden") or field.get("reference"), (form["id"], field["name"])
            assert sources.get(field["name"]) not in ("server", "currentUser"), (form["id"], field["name"])
            if sources.get(field["name"]) == "upload":  # Story 22.7: an upload, never a key typed in
                assert field.get("upload"), (form["id"], field["name"])
    spec = validate_frontend_spec_data(screens.spec).normalized
    assert not [issue for issue in check_spec_pair(spec, backend) if issue.code == "FE_FIELD_SOURCE"]


def test_each_source_in_the_form(tmp_path):
    """`currentUser` (the owner) is not shown; `route` is a hidden field filled from the page; `reference` a picker;
    `input` the 22.5 component for its type."""
    from test_policies import policy_spec

    backend, _, contract, screens = _plan(policy_spec(tmp_path), {})
    assert _request_sources(contract, "task.create")["ownerId"] == "currentUser"
    forms = {form["id"]: {f["name"]: f for f in form["fields"]} for form in screens.spec["forms"]}
    in_project = forms["task_create_in_project"]
    assert "ownerId" not in in_project, "the server sets the owner from the signed-in user"
    assert in_project["projectId"] == {
        "name": "projectId",
        "type": "string",
        "hidden": True,
        "value": "$route.id",
        "required": True,
    }
    assert forms["task_update"]["projectId"]["reference"]["listOperation"] == "project.list"
    assert in_project["status"]["type"] == "enum" and in_project["dueDate"]["type"] == "date"


def test_a_child_on_its_parents_page_takes_the_route_elsewhere_a_picker(tmp_path):
    """Flashcards: a card added on its deck's page has the deck from the route; moving a card to another deck (its
    edit form) picks the deck by name from `deck.list`, searched on the server when the list has search."""
    backend, screens = APPS_WITH_FIXTURE["flashcards"]
    forms = {form["id"]: {f["name"]: f for f in form["fields"]} for form in screens.spec["forms"]}
    assert forms["card_create_in_deck"]["deckId"]["value"] == "$route.id"
    picker = forms["card_update"]["deckId"]
    assert picker["label"] == "Deck" and picker["reference"]["labelField"] == "name"
    assert "searchParam" not in picker["reference"], "deck.list has no search: the picker filters its first page"
    shop_backend, shop = APPS_WITH_FIXTURE["shop"]
    searched = [
        f["reference"]
        for form in shop.spec["forms"]
        for f in form["fields"]
        if (f.get("reference") or {}).get("searchParam")
    ]
    assert all(ref["searchParam"] == "q" for ref in searched)


def test_a_parent_without_a_list_gets_one_to_pick_from():
    """Step 5 (deferred from 10.0b): `x-bga.ref.listOperation` is null when the parent has no list; code adds a
    paginated list searched on the parent's label, and the picker uses it."""
    backend, raw = _example("two-entity")
    backend = {**backend, "operations": [op for op in backend["operations"] if op["operationId"] != "project.list"]}
    contract = build_contract(backend, build_plan(backend))
    assert any(
        ((prop.get("x-bga") or {}).get("ref") or {}).get("listOperation", "x") is None
        for schema in contract["components"]["schemas"].values()
        for prop in (schema.get("properties") or {}).values()
    )
    extended, _, notes = ensure_aggregates(backend, {})
    added = next(op for op in extended["operations"] if op["operationId"] == "project.list")
    assert added["path"] == "/projects" and added["pagination"] and "name" in json.dumps(added["search"])
    assert any("project.list added" in note["message"] for note in notes)
    assert validate_spec_data(extended).report.valid
    _, _, _, screens = _plan(backend, raw)
    picker = next(f for form in screens.spec["forms"] for f in form["fields"] if f.get("reference"))
    assert picker["reference"]["listOperation"] == "project.list" and picker["reference"]["searchParam"] == "q"


def test_the_picker_component():
    """The kit's picker: a Combobox (Popover + Command) on the parent's list, server search with `q` when the list has
    it (no browser filter), else the first page filtered in the browser; it shows the label, sends the id, and loads a
    chosen record the first page does not hold through the parent's `get`."""
    picker = (KIT / "form/ReferenceField.tsx").read_text()
    assert "<Popover" in picker and "<Command shouldFilter={!reference.searchParam}>" in picker
    assert "useOperationQuery(reference.listOperation, params)" in picker
    assert "params[reference.searchParam] = deferred" in picker
    assert "onChange(record.id)" in picker and "keywords={[name]}" in picker
    assert "reference.detailOperation" in picker and 'role="combobox"' in picker
    dispatch = (KIT / "form/FieldInput.tsx").read_text()
    assert "if (props.field.reference) return <ReferenceField {...props} />;" in dispatch


def test_lists_and_details_show_parents_by_name_on_mocks_and_live():
    """`FieldValue` shows a parent's summary label linked to its page and never its id; the MSW mocks present the same
    `{id, label}` summary per parent as the API (`present()` in `handlers.ts`)."""
    value = (KIT / "FieldValue.tsx").read_text()
    assert "summary?.label ? String(summary.label) : (app.entities[reference.entity]?.label" in value
    assert "String(id)" not in value
    handlers = (OVERLAY / "src/mocks/handlers.ts").read_text()
    assert "out[ref.apiName] = id === null || id === undefined ? null : { id, label:" in handlers


def test_the_picker_is_app_only_in_the_schema():
    assert "reference" not in frontend_spec_json_schema(app=False)["$defs"]["FormField"]["properties"]
    assert "FormFieldReference" not in frontend_spec_json_schema(app=False)["$defs"]
    assert "reference" in frontend_spec_json_schema()["$defs"]["FormField"]["properties"]
