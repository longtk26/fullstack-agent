"""Frontend ↔ contract consistency (Story 12.5)."""

import copy
import json

import pytest
from generation_helpers import EXAMPLES, normalized

from src.modules.shared.domain.frontend_spec import validate_frontend_spec_data
from src.orchestrator.checks.consistency import check_spec_pair

SHOP_FRONTEND = json.loads((EXAMPLES / "frontend-specs" / "shop-dynamic.json").read_text())


def issues(frontend: dict, backend: str = "shop") -> list:
    result = validate_frontend_spec_data(frontend)
    assert result.report.valid, result.report.errors
    return check_spec_pair(result.normalized, normalized(EXAMPLES / "specs" / f"{backend}.json"))


@pytest.mark.parametrize(("frontend", "backend"), [("shop-dynamic", "shop"), ("project-tracker-dynamic", "two-entity")])
def test_example_pairs_are_consistent(frontend, backend):
    spec = json.loads((EXAMPLES / "frontend-specs" / f"{frontend}.json").read_text())
    assert issues(spec, backend) == []


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
    assert {i.code for i in found} == {"CONTRACT_UNKNOWN_OPERATION"}
    assert len(found) == 6
