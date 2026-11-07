"""The screens' operations change the drafted BackendSpec only while it stays valid (2026-11-07: a bakery draft
crashed after the dashboard left out an aggregate that something else still named: the edited spec did not validate
and the draft went on with no spec)."""

import json

from src.modules.shared.domain.backend_spec import validate_spec_data
from src.orchestrator.drafting.app import _with_screen_operations

SPEC = {
    "specVersion": "1.0",
    "project": {"name": "Bakery", "description": "Wholesale orders"},
    "stack": {"framework": "fastapi", "database": "postgresql", "orm": "sqlalchemy", "migration": "alembic"},
    "entities": [{"name": "Order", "fields": [{"name": "id", "type": "uuid", "primary": True},
                                             {"name": "total", "type": "decimal", "required": True}]}],
    "operations": [
        {"operationId": "order.list", "type": "crud", "action": "list", "entity": "Order", "method": "GET",
         "path": "/orders"},
        {"operationId": "order.totalSum", "type": "aggregate", "entity": "Order", "method": "GET",
         "path": "/orders/aggregate/total-sum", "aggregate": {"fn": "sum", "field": "total"}},
    ],
    "backgroundJobs": [{"name": "nightlyTotal", "trigger": "operation:order.totalSum", "action": "log"}],
}  # fmt: skip

ADDED = {"operationId": "order.count", "type": "aggregate", "entity": "Order", "method": "GET",
         "path": "/orders/aggregate/count", "aggregate": {"fn": "count"}}  # fmt: skip


def _drafted(tmp_path):
    path = tmp_path / "backend-spec.json"
    path.write_text(json.dumps(SPEC))
    backend = validate_spec_data(json.loads(json.dumps(SPEC))).normalized
    assert backend is not None
    return path, backend


def test_a_removal_that_breaks_the_spec_keeps_the_aggregate(tmp_path):
    path, backend = _drafted(tmp_path)
    edited, notes = _with_screen_operations(path, backend, [ADDED], {"order.totalSum"})
    ids = [op["operationId"] for op in edited["operations"]]
    assert "order.totalSum" in ids and "order.count" in ids
    assert "order.count" in path.read_text()
    assert len(notes) == 1 and "stay in the BackendSpec" in notes[0]["message"]


def test_an_edit_that_stays_valid_is_written(tmp_path):
    path, backend = _drafted(tmp_path)
    edited, notes = _with_screen_operations(path, backend, [ADDED], set())
    assert [op["operationId"] for op in edited["operations"]][-1] == "order.count" and notes == []


def test_an_addition_that_breaks_the_spec_leaves_it_as_drafted(tmp_path):
    path, backend = _drafted(tmp_path)
    before = path.read_text()
    broken = {**ADDED, "entity": "Missing"}
    edited, notes = _with_screen_operations(path, backend, [broken], set())
    assert edited is backend and path.read_text() == before
    assert "were not added" in notes[0]["message"]
