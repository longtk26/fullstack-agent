"""Screens from the contract (Story 22.3): the screen planner writes every page, form and binding of an app from the
completed outline and the contract; every operation is on a screen or an action, and the pair check passes."""

import json
import os
import sys
from pathlib import Path

import pytest

from src.modules.shared.domain.backend_spec import validate_spec_data
from src.modules.shared.domain.frontend_spec import uncovered_operations, validate_frontend_spec_data
from src.orchestrator.backend.planner import build_plan
from src.orchestrator.checks.consistency import check_spec_pair
from src.orchestrator.frontend.app.outline import complete_outline
from src.orchestrator.frontend.app.screens import app_frontend_spec, ensure_aggregates
from src.orchestrator.frontend.planner import plan_frontend
from src.orchestrator.integration.contract import build_contract

sys.path.insert(0, str(Path(__file__).parent))

EXAMPLES = Path(__file__).parents[2] / "examples"
SNAPSHOTS = Path(__file__).parent / "fixtures" / "app-screens"
APPS = {  # BackendSpec example → its outline (None: what code fills from the BackendSpec alone)
    "flashcards": "flashcards",
    "two-entity": "project-tracker",
    "shop": None,
    "task-management": None,
}


def _plan(backend: dict, raw_outline: dict) -> tuple[dict, dict, dict, object]:
    outline, _ = complete_outline(raw_outline, backend, build_contract(backend, build_plan(backend)))
    backend, outline, _ = ensure_aggregates(backend, outline)
    assert validate_spec_data(backend).report.valid
    contract = build_contract(backend, build_plan(backend))
    return backend, outline, contract, app_frontend_spec(backend, outline, {"colorScheme": "light-dark"}, contract)


def _example(name: str) -> tuple[dict, dict]:
    backend = validate_spec_data(json.loads((EXAMPLES / "specs" / f"{name}.json").read_text())).normalized
    outline_name = APPS[name]
    raw = json.loads((EXAMPLES / "app-outlines" / f"{outline_name}.json").read_text()) if outline_name else {}
    return backend, raw


def _bindings(spec: dict) -> dict:
    """What calls what: per page, each section's component and binding; the forms; the navigation."""
    pages = {
        page["route"]: [
            {key: section[key] for key in ("id", "component", "data", "form") if key in section}
            | {"actions": [a["id"] for a in (section.get("content") or {}).get("actions") or []]}
            for section in page["sections"]
        ]
        for page in spec["pages"]
    }
    forms = {
        form["id"]: {
            "operationId": form["operationId"],
            "fields": [
                field["name"] + ("=" + field["value"] if field.get("hidden") else "") for field in form["fields"]
            ],
        }
        for form in spec.get("forms") or []
    }
    return {"pages": pages, "forms": forms, "navigation": spec["layout"]["header"]["navigation"]}


@pytest.mark.parametrize("name", sorted(APPS))
def test_every_operation_is_on_a_screen_and_the_pair_check_passes(name):
    backend, raw = _example(name)
    backend, _, contract, screens = _plan(backend, raw)
    result = validate_frontend_spec_data(screens.spec)
    assert result.report.valid, result.report.errors
    assert check_spec_pair(result.normalized, backend) == [], "no errors and no warnings (FE_FIELD_SOURCE included)"
    assert uncovered_operations(screens.spec, contract) == []
    assert screens.unresolved == [], "nothing unplaced"
    assert not any(page["route"].startswith("/manage") for page in screens.spec["pages"]), "no Manage area"


@pytest.mark.parametrize("name", sorted(APPS))
def test_the_planner_is_deterministic_and_snapshotted(name):
    backend, raw = _example(name)
    first = _bindings(_plan(backend, raw)[3].spec)
    assert first == _bindings(_plan(backend, raw)[3].spec)
    snapshot = SNAPSHOTS / f"{name}.json"
    text = json.dumps(first, indent=2, ensure_ascii=False) + "\n"
    if os.environ.get("UPDATE_SNAPSHOTS") or not snapshot.exists():
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_text(text)
    assert text == snapshot.read_text(), f"{name} screens changed: review, then rerun with UPDATE_SNAPSHOTS=1"


def test_a_child_is_created_from_its_parent_with_the_parent_from_the_route():
    backend, raw = _example("flashcards")
    spec = _plan(backend, raw)[3].spec
    forms = {form["id"]: form for form in spec["forms"]}
    deck_field = next(f for f in forms["card_create_in_deck"]["fields"] if f["name"] == "deckId")
    assert deck_field == {"name": "deckId", "type": "string", "hidden": True, "value": "$route.id", "required": True}
    assert "card_create" not in forms, "no standalone create that would ask for a deck id"
    deck = next(page for page in spec["pages"] if page["route"] == "/decks/[id]")
    tabs = {s["id"]: s for s in deck["sections"] if (s.get("content") or {}).get("tab")}
    assert tabs["cards-tab"]["data"]["params"] == {"deckId": "$route.id"}
    assert tabs["cards-tab"]["content"]["create"]["page"] == "decks-id-cards-new"
    assert tabs["card-list-due-tab"]["data"]["operationId"] == "card.listDue", "a custom list filtered by its parent"
    assert "deckId" not in tabs["cards-tab"]["data"]["fields"], "the parent is the page"
    for form in spec["forms"]:  # no form asks for an id
        assert not any(f["name"].endswith("Id") and not f.get("hidden") for f in form["fields"]), form["id"]


def test_custom_operations_become_actions_and_lists():
    backend, raw = _example("flashcards")
    spec = _plan(backend, raw)[3].spec
    card = next(page for page in spec["pages"] if page["route"] == "/cards/[id]")
    detail = card["sections"][0]
    review = next(a for a in detail["content"]["actions"] if a["id"] == "review")
    assert review["operationId"] == "card.review" and review["form"] == "card_review", "a body opens a dialog"
    assert review["params"] == {"id": "$route.id"}
    rows = next(page for page in spec["pages"] if page["route"] == "/cards")["sections"][0]["content"]["actions"]
    assert [a["id"] for a in rows] == ["view", "edit", "delete"], "an action with a body is not a row action"
    assert next(a for a in rows if a["id"] == "delete")["confirm"]
    deck = next(page for page in spec["pages"] if page["route"] == "/decks/[id]")
    assert any(s["data"]["operationId"] == "deck.stats" for s in deck["sections"]), "a record's summary"
    assert {"label": "Due cards", "page": "cards-due"} in spec["layout"]["header"]["navigation"]


def test_dashboard_figures_are_aggregates_added_by_code():
    backend, raw = _example("two-entity")
    extended, outline, _, screens = _plan(backend, raw)
    added = {op["operationId"]: op for op in extended["operations"] if op["type"] == "aggregate"}
    assert added["task.countWhereStatusTodo"]["aggregate"] == {"fn": "count", "filters": {"status": "TODO"}}
    assert added["task.countByStatus"]["aggregate"] == {"fn": "count", "groupBy": "status"}
    home = next(page for page in screens.spec["pages"] if page["route"] == "/")
    figures = [s for s in home["sections"] if s["component"] == "AppDashboard"]
    assert [f["data"]["operationId"] for f in figures] == [
        "project.count",
        "task.countWhereStatusTodo",
        "task.countByStatus",
    ]
    assert figures[2]["content"]["kind"] == "bar"
    assert "operationId" not in json.dumps(screens.spec["app"]), "the outline carries no bindings"


def test_period_figures_count_from_the_creation_date():
    backend, raw = _example("flashcards")
    extended = _plan(backend, raw)[0]
    week = next(op for op in extended["operations"] if op["operationId"] == "reviewLog.countThisWeek")
    assert week["aggregate"] == {"fn": "count", "period": "week", "dateField": "reviewedAt"}


def test_a_record_created_from_a_parent_that_does_not_list_it():
    """`cartItem.create` needs a product, but the cart list does not filter by product: an 'Add' link on the
    product's page opens a form that takes the product from the route."""
    backend, raw = _example("shop")
    spec = _plan(backend, raw)[3].spec
    product = next(page for page in spec["pages"] if page["route"] == "/products/[id]")
    add = product["sections"][0]["content"]["actions"][0]
    assert add == {
        "id": "add-cart-items",
        "label": "Add cart item",
        "kind": "link",
        "page": "products-id-cart-items-new",
        "params": {"id": "$route.id"},
    }
    navigation = [link["page"] for link in spec["layout"]["header"]["navigation"]]
    assert navigation == ["home", "categories", "products", "cart-items", "contact-messages-new"]


def test_a_second_parent_is_typed_until_pickers_and_noted():
    import test_concurrency_rules

    backend = validate_spec_data(test_concurrency_rules.booking_spec(Path("/tmp"))).normalized
    backend, _, _, screens = _plan(backend, {})
    assert any("until pickers (22.6)" in note["message"] for note in screens.unresolved)
    issues = check_spec_pair(validate_frontend_spec_data(screens.spec).normalized, backend)
    assert {issue.code for issue in issues} == {"FE_FIELD_SOURCE"} and all(i.severity == "warning" for i in issues)


@pytest.mark.parametrize("name", sorted(APPS))
def test_the_app_plan_has_a_route_per_page_and_a_sidebar(name):
    backend, raw = _example(name)
    _, _, contract, screens = _plan(backend, raw)
    spec = validate_frontend_spec_data(screens.spec).normalized
    plan = plan_frontend(spec, contract)
    assert plan["rendering"] == "app" and plan["rendererGaps"] == []
    assert [route["route"] for route in plan["routes"]] == [page["route"] for page in screens.spec["pages"]]
    assert plan["app"]["nav"][0] == {"label": "Dashboard", "page": "home", "icon": "LayoutDashboard"}


def test_a_real_antigravity_draft_plans_cleanly():
    """Story 22.3's live check (Antigravity, 2026-11-05, "Bike Shed"): one call, no repair; replayed here. Its
    BackendSpec already has the dashboard's aggregates (written by code live), so code adds none."""
    recorded = Path(__file__).parent / "fixtures" / "drafts" / "bike-shed-antigravity"
    backend = validate_spec_data(json.loads((recorded / "backend-spec.json").read_text())).normalized
    raw = json.loads((recorded / "app-outline.json").read_text())
    extended, outline, contract, screens = _plan(backend, raw)
    assert extended["operations"] == backend["operations"], "the aggregates are found, not added again"
    spec = validate_frontend_spec_data(screens.spec)
    assert spec.report.valid and check_spec_pair(spec.normalized, extended) == []
    assert uncovered_operations(screens.spec, contract) == [] and screens.unresolved == []
    spent = next(item for item in outline["dashboard"] if item["label"] == "Spent this year")
    assert spent["operationId"] == "service.sumCostThisYear" and spent["dateField"] == "date"
    routes = [page["route"] for page in screens.spec["pages"]]
    assert "/bikes/[id]/services/new" in routes and "/services/new" not in routes


KIT = Path(__file__).parents[1] / "templates" / "nextjs_overlay" / "files" / "dynamic" / "app" / "src" / "components"
KIT = KIT / "app"


def test_the_kit_renders_every_app_section():
    """Story 22.4: each app section the planner writes has its kit component, picked by `AppSection`."""
    from src.modules.shared.domain.frontend_spec.app import APP_SECTIONS

    switch = (KIT / "AppSection.tsx").read_text()
    for name in APP_SECTIONS:
        assert f'case "{name}":' in switch and (KIT / f"{name}.tsx").is_file(), name


def test_an_app_scaffolds_the_kit_and_its_data(tmp_path):
    from src.orchestrator.frontend.scaffold import scaffold_frontend

    backend, raw = _example("flashcards")
    _, _, contract, screens = _plan(backend, raw)
    spec = validate_frontend_spec_data(screens.spec).normalized
    plan = plan_frontend(spec, contract)
    assert {"table", "dropdown-menu", "alert-dialog", "dialog", "tabs", "chart", "breadcrumb", "empty"} <= set(
        plan["shadcn"]
    )
    scaffold_frontend(tmp_path, plan, spec, contract)
    for name in ("AppList", "AppDetail", "AppForm", "AppDashboard", "AppActions", "RecordActions", "FieldValue"):
        assert (tmp_path / "src" / "components" / "app" / f"{name}.tsx").is_file(), name
    data = json.loads((tmp_path / "src/content/app.json").read_text())
    card = data["entities"]["Card"]
    assert card["references"]["deckId"] == {"summary": "deck", "entity": "Deck", "href": "/decks/[id]"}
    assert card["fields"]["dueDate"] == {"type": "date"} and card["fields"]["deck"] == {"type": "summary"}
    assert card["listOperation"] == "card.list" and data["entities"]["Deck"]["listOperation"] == "deck.list"
    assert data["routes"]["decks-id-cards-new"] == "/decks/[id]/cards/new" and data["density"] == "comfortable"
    assert data["errors"]["deck.create"][0]["code"] == "VALIDATION_ERROR"
    assert data["forms"]["card_update"]["load"] == {"operationId": "card.get", "params": {"id": "$route.id"}}
    schemas = (tmp_path / "src/components/app/form-schemas.ts").read_text()
    assert '"card_create_in_deck": { schema: cardCreateInDeckSchema' in schemas


def test_custom_and_aggregate_queries_have_their_own_cache_keys():
    """Two figures of one resource with the same parameters (`task.countByStatus`, `task.countWhereStatusTodo`) and a
    custom list beside the CRUD list (`card.listDue`) must not share a React Query cache entry (seen in 22.4)."""
    from src.orchestrator.frontend.codegen import bindings_ts, queries_ts

    backend, raw = _example("two-entity")
    _, _, contract, _ = _plan(backend, raw)
    bindings = bindings_ts(contract)
    assert '"task.countByStatus": (params) => [...taskKeys.all, "task.countByStatus", params] as const' in bindings
    assert '"task.list": (params) => taskKeys.list(params)' in bindings
    backend, raw = _example("flashcards")
    _, _, contract, _ = _plan(backend, raw)
    assert 'queryKey: [...cardKeys.all, "card.listDue", params] as const' in queries_ts(contract)


@pytest.mark.parametrize("name", sorted(APPS))
def test_attaching_an_app_spec_changes_none_of_its_links(name):
    """A generation runs `autofix_frontend_spec` on the specs it attaches. It once re-checked a link without the link's
    own `params` and pointed every record link (view, edit, add a child) at the list page (live Pantry run, 22.4)."""
    import copy

    from src.modules.shared.domain.frontend_spec.autofix import autofix_frontend_spec

    backend, raw = _example(name)
    spec = _plan(backend, raw)[3].spec
    fixed, notes = autofix_frontend_spec(copy.deepcopy(spec))
    assert fixed["pages"] == spec["pages"] and notes == []
