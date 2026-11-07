"""The contract's scenarios agree with each other and with the data (2026-11-08): the mocks answered five of a real
draft's scenarios differently from what the contract expected, and the scenarios were the ones at fault.

The draft (`fixtures/scenario-specs/volunteer-shifts.json`, agy) has an attendance per shift registration (a unique
reference: one-to-one), one attendance per volunteer and shift (`uniqueTogether`), and attendances that are final once
recorded, with `RECORDED` their only status (`immutableAfter`: every seeded attendance is locked)."""

import json
import re
from pathlib import Path

from src.modules.shared.domain.backend_spec import validate_spec_data
from src.orchestrator.backend.planner import build_plan
from src.orchestrator.integration.contract import UNKNOWN_ID, build_contract

SPEC = Path(__file__).parent / "fixtures" / "scenario-specs" / "volunteer-shifts.json"
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def _contract() -> dict:
    spec = validate_spec_data(json.loads(SPEC.read_text())).normalized
    assert spec is not None
    return build_contract(spec, build_plan(spec))


def _scenarios(contract: dict, op_id: str) -> dict[str, dict]:
    for methods in contract["paths"].values():
        for op in methods.values():
            if isinstance(op, dict) and op.get("operationId") == op_id:
                return {s["name"]: s for s in op["x-bga"].get("scenarios") or []}
    raise AssertionError(op_id)


def test_every_reference_a_scenario_sends_exists_unless_it_tests_an_unknown_one():
    """`_fresh` made "Scenario <id>" for a unique id; a unique reference is a free parent in every create built from
    the success (not only the success)."""
    contract = _contract()
    fixtures = contract["x-bga"]["fixtures"]
    ids = {str(row.get("id")) for rows in fixtures.values() for row in rows}
    for name, scenario in _scenarios(contract, "attendance.create").items():
        for field in ("shiftId", "registrationId", "volunteerId"):
            value = (scenario.get("body") or {}).get(field)
            if value is None or name == f"unknown {field}":
                continue
            assert UUID.match(str(value)), (name, field, value)
            assert str(value) in ids, (name, field, value)
    assert _scenarios(contract, "attendance.create")["unknown registrationId"]["body"]["registrationId"] == UNKNOWN_ID


def test_a_rules_scenario_runs_as_a_role_that_may_call_the_operation():
    create = _scenarios(_contract(), "attendance.create")
    assert create["second attendance"].get("user") == "demo-coordinator@example.com"
    assert create["second attendance"]["expect"] == {"status": 409, "code": "CONFLICT"}


def test_each_conflict_scenario_conflicts_on_one_thing():
    """The registration's duplicate keeps a free volunteer and shift pair, and the pair's duplicate a free
    registration: else two conflicts answer and which comes first is the server's choice."""
    contract = _contract()
    rows = contract["x-bga"]["fixtures"]["Attendance"]
    pairs = {(r["shiftId"], r["volunteerId"]) for r in rows}
    registrations = {r["registrationId"] for r in rows}
    create = _scenarios(contract, "attendance.create")
    reg = create["duplicate registrationId"]["body"]
    assert reg["registrationId"] in registrations and (reg["shiftId"], reg["volunteerId"]) not in pairs
    pair = create["duplicate"]["body"]
    assert (pair["shiftId"], pair["volunteerId"]) in pairs and pair["registrationId"] not in registrations


def test_nothing_expects_to_get_past_a_lock_every_record_has():
    """Every seeded attendance is RECORDED (its only status) and recorded ones are final: an update can only be
    refused. The answers given before the lock stay; nothing expects a success or a conflict."""
    update = _scenarios(_contract(), "attendance.update")
    assert "success" not in update and "duplicate registrationId" not in update
    assert update["locked record"]["expect"] == {"status": 409, "code": "RESOURCE_LOCKED"}
    assert {"no token", "unknown id", "wrong role"} <= set(update)


BAKERY = SPEC.parent / "bakery-wholesale.json"


def test_another_users_record_stays_another_users_when_records_are_locked():
    """2026-11-07, a bakery draft (agy): orders are final once delivered and the other café's orders are all
    delivered. The rules plugin moved "another user's record" off the locked order onto the first open one and gave it
    that order's owner: the mock answered 200 where the contract expected 404. A refusal answered before the lock
    reaches a locked record as well, so it stays where it is."""
    spec = validate_spec_data(json.loads(BAKERY.read_text())).normalized
    assert spec is not None
    contract = build_contract(spec, build_plan(spec))
    fixtures = contract["x-bga"]["fixtures"]
    users = {row["email"]: str(row["id"]) for row in fixtures["User"]}
    orders = {str(row["id"]): row for row in fixtures["Order"]}
    checked = 0
    for op_id in ("order.get", "order.update"):
        scenario = _scenarios(contract, op_id)["another user's record"]
        record = orders[scenario["params"]["id"]]
        assert scenario.get("user") in users, (op_id, scenario)
        assert str(record["ownerId"]) != users[scenario["user"]], (op_id, scenario, record)
        checked += 1
    assert checked == 2
