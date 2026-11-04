"""Frontend ↔ contract consistency (Story 12.5)."""

import copy
import json

import pytest
from generation_helpers import EXAMPLES, normalized

from src.modules.shared.domain.backend_spec import Severity
from src.modules.shared.domain.frontend_spec import validate_frontend_spec_data
from src.orchestrator.checks.consistency import check_spec_pair, closest_field, reconcile_spec_pair

SHOP_FRONTEND = json.loads((EXAMPLES / "frontend-specs" / "shop-dynamic.json").read_text())


def issues(frontend: dict, backend: str = "shop") -> list:
    result = validate_frontend_spec_data(frontend)
    assert result.report.valid, result.report.errors
    return check_spec_pair(result.normalized, normalized(EXAMPLES / "specs" / f"{backend}.json"))


@pytest.mark.parametrize(("frontend", "backend"), [("shop-dynamic", "shop"), ("project-tracker-dynamic", "two-entity")])
def test_example_pairs_are_consistent(frontend, backend):
    spec = json.loads((EXAMPLES / "frontend-specs" / f"{frontend}.json").read_text())
    assert [i for i in issues(spec, backend) if i.severity != Severity.WARNING] == []


def _mutate(change) -> dict:
    spec = copy.deepcopy(SHOP_FRONTEND)
    change(spec)
    return spec


CASES = [
    ("CONTRACT_UNKNOWN_OPERATION", "/pages/1/sections/0/data/operationId", "/operations",
     lambda s: s["pages"][1]["sections"][0]["data"].update(operationId="product.search")),
    ("CONTRACT_UNKNOWN_OPERATION", "/forms/1/operationId", "/operations",
     lambda s: s["forms"][1].update(operationId="contact.send")),
    ("CONTRACT_METHOD_MISMATCH", "/pages/3/sections/0/data/operationId", "/operations/4",
     lambda s: s["pages"][3]["sections"][0]["data"].update(operationId="cartItem.create")),
    ("CONTRACT_METHOD_MISMATCH", "/forms/0/operationId", "/operations/3",
     lambda s: s["forms"][0].update(operationId="cartItem.list")),
    ("CONTRACT_PARAM_MISMATCH", "/pages/1/sections/0/data/params/category", "/operations/1",
     lambda s: s["pages"][1]["sections"][0]["data"]["params"].update(category="tea")),
    ("CONTRACT_PARAM_MISMATCH", "/pages/1/sections/0/data/params/sort", "/operations/1",
     lambda s: s["pages"][1]["sections"][0]["data"]["params"].update(sort="-stock")),
    ("CONTRACT_PARAM_MISMATCH", "/pages/1/sections/0/data/params/limit", "/operations/1",
     lambda s: s["pages"][1]["sections"][0]["data"]["params"].update(limit=500)),
    ("CONTRACT_PARAM_MISMATCH", "/pages/2/sections/0/data/params", "/operations/2",
     lambda s: s["pages"][2]["sections"][0]["data"].update(params={})),
    ("CONTRACT_FIELD_MISSING", "/pages/1/sections/0/data/fields/1", "/entities/1/fields",
     lambda s: s["pages"][1]["sections"][0]["data"]["fields"].__setitem__(1, "salePrice")),
    ("CONTRACT_FIELD_MISSING", "/forms/1/fields/2/name", "/entities/3/fields",
     lambda s: s["forms"][1]["fields"][2].update(name="body")),
    ("CONTRACT_FIELD_MISSING", "/forms/0/fields", "/entities/2/fields/2",
     lambda s: s["forms"][0].update(fields=s["forms"][0]["fields"][:1])),
    ("CONTRACT_FIELD_TYPE_MISMATCH", "/forms/0/fields/1/type", "/entities/2/fields/2",
     lambda s: s["forms"][0]["fields"][1].update(type="boolean")),
    ("CONTRACT_FIELD_TYPE_MISMATCH", "/forms/1/fields/0/required", "/entities/3/fields/1",
     lambda s: s["forms"][1]["fields"][0].update(required=False)),
]  # fmt: skip


@pytest.mark.parametrize(("code", "path", "backend_path", "change"), CASES, ids=[f"{c[0]}:{c[1]}" for c in CASES])
def test_mismatches_point_at_both_specs(code, path, backend_path, change):
    found = [(i.code, i.path, i.backend_path) for i in issues(_mutate(change))]
    assert (code, path, backend_path) in found, found


def test_form_enum_and_date_fields_must_match_the_contract():
    frontend = json.loads((EXAMPLES / "frontend-specs" / "project-tracker-dynamic.json").read_text())
    task_form = frontend["forms"][1]["fields"]
    task_form[2] = {"name": "status", "type": "string"}  # free text for an enum
    task_form[4] = {"name": "dueDate", "type": "datetime"}  # the contract field is a date
    found = {(i.code, i.path) for i in issues(frontend, "two-entity")}
    assert ("CONTRACT_FIELD_TYPE_MISMATCH", "/forms/1/fields/2/type") in found
    assert ("CONTRACT_FIELD_TYPE_MISMATCH", "/forms/1/fields/4/type") in found


def test_a_frontend_for_another_backend_fails_on_every_binding():
    found = issues(SHOP_FRONTEND, "two-entity")
    errors = [i for i in found if i.severity != Severity.WARNING]
    assert {i.code for i in errors} == {"CONTRACT_UNKNOWN_OPERATION"}
    assert len(errors) == 6


def test_form_load_consistency():
    frontend = json.loads((EXAMPLES / "frontend-specs" / "project-tracker-dynamic.json").read_text())
    # editProject is at forms[2]
    assert [i for i in issues(frontend, "two-entity") if i.severity != Severity.WARNING] == []

    # 1. Unknown operation
    f1 = copy.deepcopy(frontend)
    f1["forms"][2]["load"]["operationId"] = "unknown.get"
    found = {(i.code, i.path) for i in issues(f1, "two-entity")}
    assert ("CONTRACT_UNKNOWN_OPERATION", "/forms/2/load/operationId") in found

    # 2. Method mismatch (POST instead of GET)
    f2 = copy.deepcopy(frontend)
    f2["forms"][2]["load"]["operationId"] = "project.create"
    found = {(i.code, i.path) for i in issues(f2, "two-entity")}
    assert ("CONTRACT_METHOD_MISMATCH", "/forms/2/load/operationId") in found

    # 3. Field missing in loaded record
    f3 = copy.deepcopy(frontend)
    f3["forms"][2]["fields"].append({"name": "nonExistentField"})
    found = {(i.code, i.path) for i in issues(f3, "two-entity")}
    assert ("CONTRACT_FIELD_MISSING", "/forms/2/fields/2/name") in found


def test_section_controls_consistency():
    frontend = json.loads((EXAMPLES / "frontend-specs" / "project-tracker-dynamic.json").read_text())
    # project.list has sort: ["name", "createdAt"], no filters, no search
    table_section = frontend["pages"][1]["sections"][0]
    table_section["content"] = {"controls": {"sort": ["name"]}}
    assert [i for i in issues(frontend, "two-entity") if i.severity != Severity.WARNING] == []

    # 1. Search requested but operation has no search parameter
    f1 = copy.deepcopy(frontend)
    f1["pages"][1]["sections"][0]["content"]["controls"]["search"] = True
    found = {(i.code, i.path) for i in issues(f1, "two-entity")}
    assert ("CONTRACT_PARAM_MISMATCH", "/pages/1/sections/0/content/controls/search") in found

    # 2. Filter not declared
    f2 = copy.deepcopy(frontend)
    f2["pages"][1]["sections"][0]["content"]["controls"]["filters"] = ["nonExistentFilter"]
    found = {(i.code, i.path) for i in issues(f2, "two-entity")}
    assert ("CONTRACT_PARAM_MISMATCH", "/pages/1/sections/0/content/controls/filters/0") in found

    # 3. Sort field not declared
    f3 = copy.deepcopy(frontend)
    f3["pages"][1]["sections"][0]["content"]["controls"]["sort"] = ["unsupportedSort"]
    found = {(i.code, i.path) for i in issues(f3, "two-entity")}
    assert ("CONTRACT_PARAM_MISMATCH", "/pages/1/sections/0/content/controls/sort/0") in found


def test_section_actions_consistency():
    frontend = json.loads((EXAMPLES / "frontend-specs" / "project-tracker-dynamic.json").read_text())
    table_section = frontend["pages"][1]["sections"][0]
    table_section["content"] = {
        "actions": [
            {"id": "view", "label": "View", "kind": "link", "page": "project", "params": {"id": "$record.id"}},
            {
                "id": "delete",
                "label": "Delete",
                "kind": "mutation",
                "operationId": "project.delete",
                "params": {"id": "$record.id"},
                "confirm": "Delete project?",
            },
        ]
    }
    assert [i for i in issues(frontend, "two-entity") if i.severity != Severity.WARNING] == []

    # 1. Link action with unknown page (caught by validator)
    f1 = copy.deepcopy(frontend)
    f1["pages"][1]["sections"][0]["content"]["actions"][0]["page"] = "non-existent-page"
    val_report = validate_frontend_spec_data(f1).report
    assert any(
        i.code == "FE_UNKNOWN_PAGE" and i.path == "/pages/1/sections/0/content/actions/0/page"
        for i in val_report.errors
    )

    # 2. Mutation action with unknown operation
    f2 = copy.deepcopy(frontend)
    f2["pages"][1]["sections"][0]["content"]["actions"][1]["operationId"] = "unknown.delete"
    found = {(i.code, i.path) for i in issues(f2, "two-entity")}
    assert ("CONTRACT_UNKNOWN_OPERATION", "/pages/1/sections/0/content/actions/1/operationId") in found

    # 3. Mutation action calling GET
    f3 = copy.deepcopy(frontend)
    f3["pages"][1]["sections"][0]["content"]["actions"][1]["operationId"] = "project.get"
    found = {(i.code, i.path) for i in issues(f3, "two-entity")}
    assert ("CONTRACT_METHOD_MISMATCH", "/pages/1/sections/0/content/actions/1/operationId") in found

    # 4. DELETE mutation action without confirm
    f4 = copy.deepcopy(frontend)
    del f4["pages"][1]["sections"][0]["content"]["actions"][1]["confirm"]
    found = {(i.code, i.path) for i in issues(f4, "two-entity")}
    assert ("CONTRACT_PARAM_MISMATCH", "/pages/1/sections/0/content/actions/1/confirm") in found


def test_stats_data_consistency():
    frontend = json.loads((EXAMPLES / "frontend-specs" / "project-tracker-dynamic.json").read_text())
    assert [i for i in issues(frontend, "two-entity") if i.severity != Severity.WARNING] == []

    # Field missing in stats response
    f1 = copy.deepcopy(frontend)
    f1["pages"][0]["sections"][0]["content"]["items"][0]["data"]["value"] = "nonExistentField"
    found = {(i.code, i.path) for i in issues(f1, "two-entity")}
    assert ("CONTRACT_FIELD_MISSING", "/pages/0/sections/0/content/items/0/data/value") in found


def test_uncovered_operations_warning_and_manage_area():
    from src.modules.shared.domain.frontend_spec import add_manage_area
    from src.orchestrator.integration.contract import build_contract

    backend_spec = normalized(EXAMPLES / "specs" / "two-entity.json")
    contract = build_contract(backend_spec)
    frontend = json.loads((EXAMPLES / "frontend-specs" / "project-tracker-dynamic.json").read_text())

    # Initial check: task.get and task.update are uncovered in project-tracker-dynamic
    warnings = [i for i in check_spec_pair(frontend, backend_spec) if i.code == "FE_OPERATION_UNUSED"]
    assert any("task.get" in w.message for w in warnings)
    assert any("task.update" in w.message for w in warnings)

    # After add_manage_area: all operations are covered
    managed_spec, notes = add_manage_area(frontend, contract)
    assert notes == []  # two-entity has no sign-in operations
    all_issues = check_spec_pair(managed_spec, backend_spec)
    assert all_issues == []

    # Idempotence: running add_manage_area again produces identical spec
    managed_again, notes_again = add_manage_area(managed_spec, contract)
    assert managed_again == managed_spec
    assert notes_again == []


def test_reconcile_spec_pair_heals_unbacked_and_invalid_operations():
    backend_spec = normalized(EXAMPLES / "specs" / "shop.json")
    frontend = copy.deepcopy(SHOP_FRONTEND)

    # 1. Unbacked auth.signin form operation
    frontend["forms"][1]["operationId"] = "auth.signin"

    # 2. Unknown action mutation
    frontend["pages"][0]["sections"][0]["content"] = {
        "actions": [
            {"id": "action1", "label": "Unknown Action", "kind": "mutation", "operationId": "dangling.op"},
        ]
    }
    # A row action of the cart items table: its path parameter comes from the row (`$record`)
    frontend["pages"][3]["sections"][0]["component"] = "DataTable"
    frontend["pages"][3]["sections"][0]["content"] = {
        "actions": [{"id": "deleteItem", "label": "Delete", "kind": "mutation", "operationId": "cartItem.delete"}]
    }

    # 3. Invalid form load
    frontend["forms"][0]["load"] = {"operationId": "auth.me"}

    # 4. Unknown section data operation
    frontend["pages"][1]["sections"][0]["data"] = {"operationId": "nonexistent.list"}

    # 5. Missing seed asset reference
    backend_copy = copy.deepcopy(backend_spec)
    backend_copy["seed"] = [{"entity": "Category", "records": [{"name": "Coffee", "icon": "asset:coffee-logo"}]}]

    # Run reconciliation
    healed, notes = reconcile_spec_pair(frontend, backend_copy)

    # Verify missing seed asset was auto-declared in frontend.assets
    assert any(a.get("id") == "coffee-logo" for a in healed.get("assets", []))
    assert any("coffee-logo" in n["message"] for n in notes)

    # Verify form operationId is reset to None (so it becomes a client-only form)
    assert healed["forms"][1]["operationId"] is None
    # Verify dangling mutation was converted to link
    assert healed["pages"][0]["sections"][0]["content"]["actions"][0]["kind"] == "link"
    assert healed["pages"][0]["sections"][0]["content"]["actions"][0].get("operationId") is None
    # Verify missing confirm on DELETE action was automatically added, and the id taken from the row
    delete_action = healed["pages"][3]["sections"][0]["content"]["actions"][0]
    assert delete_action.get("confirm") is not None
    assert delete_action["params"] == {"id": "$record.id"}
    # Verify invalid load was removed
    assert "load" not in healed["forms"][0]
    # Verify invalid section data binding was removed
    assert "data" not in healed["pages"][1]["sections"][0]
    # Verify notes were produced
    assert any("auth.signin" in n["message"] for n in notes)

    # Verify check_spec_pair now reports zero fatal consistency errors for those healed parts
    remaining_issues = check_spec_pair(healed, backend_copy)
    errors = [i for i in remaining_issues if i.severity != Severity.WARNING]
    assert errors == []


def _reconcile_shop(change) -> tuple[dict, list[dict], dict]:
    backend_spec = normalized(EXAMPLES / "specs" / "shop.json")
    frontend = _mutate(change)
    before = copy.deepcopy(frontend)
    healed, notes = reconcile_spec_pair(frontend, backend_spec)
    assert frontend == before, "reconcile works on a copy"
    return healed, notes, backend_spec


def test_reconcile_fills_path_params_from_the_record_or_the_route_only():
    delete = {"id": "remove", "label": "Remove", "kind": "mutation", "operationId": "cartItem.delete", "confirm": "?"}

    def change(spec):
        # Record context: a DataTable of cart items
        spec["pages"][3]["sections"][0]["component"] = "DataTable"
        spec["pages"][3]["sections"][0]["content"] = {"actions": [copy.deepcopy(delete)]}
        # Route context: an action bar on /products/[id]
        spec["pages"][2]["sections"].append(
            {"id": "bar", "component": "ActionBar", "content": {"actions": [copy.deepcopy(delete)]}}
        )
        # Neither: an action bar on /contact
        spec["pages"][4]["sections"].append(
            {"id": "bar", "component": "ActionBar", "content": {"actions": [copy.deepcopy(delete)]}}
        )

    healed, notes, backend_spec = _reconcile_shop(change)
    assert healed["pages"][3]["sections"][0]["content"]["actions"][0]["params"] == {"id": "$record.id"}
    assert healed["pages"][2]["sections"][-1]["content"]["actions"][0]["params"] == {"id": "$route.id"}
    unfilled = healed["pages"][4]["sections"][-1]["content"]["actions"][0]
    assert "id" not in (unfilled.get("params") or {})
    assert any(
        n["path"] == "/pages/4/sections/2/content/actions/0/params" and "Could not fill" in n["message"] for n in notes
    )
    # Left for the check to report, never guessed as `$route.id` on a page without `[id]`
    assert any(
        i.code == "CONTRACT_PARAM_MISMATCH" and i.path.startswith("/pages/4/sections/2")
        for i in check_spec_pair(healed, backend_spec)
    )


def test_reconcile_notes_every_rewrite():
    def change(spec):
        spec["pages"][0]["sections"][0]["content"] = {
            "actions": [
                {"id": "gone", "label": "Gone", "kind": "link", "page": "no-such-page"},
                {"id": "buy", "label": "Buy", "kind": "mutation", "operationId": "order.create"},
            ]
        }
        spec["forms"][0]["fields"] = [
            {"name": "quantity", "type": "integer"},
            {"name": "giftWrap", "type": "boolean"},
        ]

    healed, notes, _ = _reconcile_shop(change)
    by_path = {n["path"]: n["message"] for n in notes}
    link, converted = healed["pages"][0]["sections"][0]["content"]["actions"]
    assert (
        link["page"] == "home"
        and "unknown page 'no-such-page'" in by_path["/pages/0/sections/0/content/actions/0/page"]
    )
    assert converted["kind"] == "link"
    assert "converted to a link to 'home'" in by_path["/pages/0/sections/0/content/actions/1"]
    # Form 'addToCart' (cartItem.create): giftWrap removed, the required productId added hidden; both noted
    assert [f["name"] for f in healed["forms"][0]["fields"]] == ["quantity", "productId"]
    assert "'giftWrap'" in by_path["/forms/0/fields/1"]
    assert "'productId'" in by_path["/forms/0/fields"] and "hidden" in by_path["/forms/0/fields"]


def test_reconcile_never_rewrites_the_backend_seed():
    backend_spec = normalized(EXAMPLES / "specs" / "shop.json")
    backend_spec["seed"] = [
        {
            "entity": "Category",
            "records": [{"name": "Tea", "icon": "asset:tea-icon"}, {"name": "X", "icon": "asset:Bad_ID"}],
        }
    ]
    seed_before = copy.deepcopy(backend_spec["seed"])
    healed, notes = reconcile_spec_pair(copy.deepcopy(SHOP_FRONTEND), backend_spec)
    assert backend_spec["seed"] == seed_before
    assert any(a["id"] == "tea-icon" and a["source"] == "placeholder" for a in healed["assets"])
    assert not any(a["id"].lower() == "bad-id" for a in healed["assets"])
    assert any("asset:Bad_ID" in n["message"] for n in notes)
    # The remaining mismatch is a warning (the site shows a placeholder), not a SPEC_INVALID error
    seed_issues = [i for i in check_spec_pair(healed, backend_spec) if "Bad_ID" in i.message]
    assert seed_issues and all(i.severity == Severity.WARNING for i in seed_issues)


def test_a_custom_operation_without_a_declared_response_is_a_backend_fix(tmp_path):
    backend = json.loads((EXAMPLES / "specs" / "two-entity.json").read_text())
    backend["operations"].append(
        {"operationId": "project.summary", "type": "custom", "method": "GET", "path": "/projects/summary"}
    )
    (tmp_path / "backend.json").write_text(json.dumps(backend))
    frontend = json.loads((EXAMPLES / "frontend-specs" / "project-tracker-dynamic.json").read_text())
    frontend["pages"][0]["sections"][0]["content"]["items"][0]["data"] = {
        "operationId": "project.summary",
        "value": "openTasks",
    }
    found = [
        i
        for i in check_spec_pair(frontend, normalized(tmp_path / "backend.json"))
        if i.code == "CONTRACT_FIELD_MISSING"
    ]
    assert len(found) == 1 and found[0].backend_path == f"/operations/{len(backend['operations']) - 1}"
    assert '"response": {"properties"' in found[0].hint, "the hint says where to declare the field"


def test_a_list_section_needs_an_operation_that_returns_a_list(tmp_path):
    backend = json.loads((EXAMPLES / "specs" / "two-entity.json").read_text())
    backend["operations"].append(
        {
            "operationId": "project.overview",
            "type": "custom",
            "method": "GET",
            "path": "/projects/overview",
            "response": {"properties": [{"name": "name", "type": "string"}]},
        }
    )
    frontend = json.loads((EXAMPLES / "frontend-specs" / "project-tracker-dynamic.json").read_text())
    section = next(s for p in frontend["pages"] for s in p["sections"] if s["component"] == "CardGrid")
    section["data"] = {"operationId": "project.overview", "fields": ["name"]}

    def shape_issues():
        (tmp_path / "backend.json").write_text(json.dumps(backend))
        found = check_spec_pair(frontend, normalized(tmp_path / "backend.json"))
        return [i for i in found if i.code == "CONTRACT_SHAPE_MISMATCH"]

    assert len(shape_issues()) == 1 and '"type": "array"' in shape_issues()[0].hint
    backend["operations"][-1]["response"]["type"] = "array"
    assert shape_issues() == [], "declared as a list: the renderer can draw it"


def test_reconcile_renames_response_fields_to_the_closest_one_or_drops_them():
    """A misnamed response field (`totalValue` for `totalStockValue`) is fixed in code, never left for review."""
    frontend = json.loads((EXAMPLES / "frontend-specs" / "project-tracker-dynamic.json").read_text())
    backend_spec = normalized(EXAMPLES / "specs" / "two-entity.json")
    frontend["pages"][0]["sections"][1]["data"]["fields"] = ["projectName", "description", "nothingLikeThis"]
    frontend["pages"][1]["sections"][0]["data"]["fields"] = ["Name", "created_at"]
    frontend["pages"][0]["sections"][0]["content"]["items"] = [
        {"label": "Newest", "data": {"operationId": "project.list", "value": "created"}},
        {"label": "Odd", "data": {"operationId": "project.list", "value": "zzz"}},
    ]
    healed, notes = reconcile_spec_pair(frontend, backend_spec)
    assert healed["pages"][0]["sections"][1]["data"]["fields"] == ["name", "description"]
    assert healed["pages"][1]["sections"][0]["data"]["fields"] == ["name", "createdAt"]
    stats = healed["pages"][0]["sections"][0]["content"]["items"]
    assert stats[0]["data"]["value"] == "createdAt" and "data" not in stats[1]
    by_path = {n["path"]: n["message"] for n in notes}
    assert "'projectName' is 'name'" in by_path["/pages/0/sections/1/data/fields/0"]
    assert "dropped" in by_path["/pages/0/sections/1/data/fields/2"]
    assert not [i for i in check_spec_pair(healed, backend_spec) if i.code == "CONTRACT_FIELD_MISSING"]


def test_closest_field_guesses_only_when_one_field_is_clearly_meant():
    assert closest_field("totalValue", ["category", "totalStockValue", "itemCount"]) == "totalStockValue"
    assert closest_field("item_count", ["itemCount", "total"]) == "itemCount"
    assert closest_field("quantiy", ["quantity", "unit"]) == "quantity"
    assert closest_field("price", ["unitPrice", "priceCents"]) is None, "two equally close fields: no guess"
    assert closest_field("name", ["title", "price"]) is None
