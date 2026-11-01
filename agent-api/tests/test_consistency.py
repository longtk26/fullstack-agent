"""Frontend ↔ contract consistency (Story 12.5)."""

import copy
import json

import pytest
from generation_helpers import EXAMPLES, normalized

from src.modules.shared.domain.backend_spec import Severity
from src.modules.shared.domain.frontend_spec import validate_frontend_spec_data
from src.orchestrator.checks.consistency import check_spec_pair, reconcile_spec_pair

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
    from src.orchestrator.contract import build_contract

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
            {"id": "deleteItem", "label": "Delete", "kind": "mutation", "operationId": "cartItem.delete"},
        ]
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
    # Verify missing confirm on DELETE action was automatically added
    assert healed["pages"][0]["sections"][0]["content"]["actions"][1].get("confirm") is not None
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
