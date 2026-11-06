"""Concurrency rules (Story 10.10): capacity under a parent's row lock, noOverlap as an exclusion constraint,
uniqueTogether as a (partial) unique index; their errors by constraint name, concurrent template tests, scenarios."""

import json
from pathlib import Path

from src.orchestrator.backend.codegen import database_files, module_files, module_tests
from src.orchestrator.backend.planner import build_plan
from src.orchestrator.integration.contract import build_contract, contract_operations
from tests.generation_helpers import normalized


def _crud(entity: str, plural: str) -> list[dict]:
    lower = entity[:1].lower() + entity[1:]
    return [
        {"operationId": f"{lower}.create", "type": "crud", "action": "create", "entity": entity, "method": "POST",
         "path": f"/{plural}"},
        {"operationId": f"{lower}.get", "type": "crud", "action": "get", "entity": entity, "method": "GET",
         "path": f"/{plural}/{{id}}"},
        {"operationId": f"{lower}.list", "type": "crud", "action": "list", "entity": entity, "method": "GET",
         "path": f"/{plural}"},
        {"operationId": f"{lower}.update", "type": "crud", "action": "update", "entity": entity, "method": "PATCH",
         "path": f"/{plural}/{{id}}"},
    ]  # fmt: skip


def booking_spec(tmp_path: Path) -> dict:
    """Workshops with seats, rooms, bookings: a workshop's active bookings fit its capacity, a room's active bookings
    never overlap, one active booking per attendee and workshop."""
    uuid_pk = {"name": "id", "type": "uuid", "primary": True}
    raw = {
        "specVersion": "1.0",
        "project": {"name": "Workshop Bookings"},
        "stack": {"framework": "fastapi", "database": "postgresql", "orm": "sqlmodel", "migration": "alembic"},
        "entities": [
            {"name": "Workshop", "fields": [uuid_pk, {"name": "name", "type": "string", "required": True,
                                                       "maxLength": 120},
                                             {"name": "capacity", "type": "integer", "required": True, "min": 1}]},
            {"name": "Room", "fields": [uuid_pk, {"name": "name", "type": "string", "required": True,
                                                   "maxLength": 80}]},
            {"name": "Booking", "fields": [
                uuid_pk,
                {"name": "workshopId", "type": "uuid", "required": True},
                {"name": "roomId", "type": "uuid", "required": True},
                {"name": "attendeeEmail", "type": "string", "required": True, "maxLength": 255},
                {"name": "startsAt", "type": "datetime", "required": True},
                {"name": "endsAt", "type": "datetime", "required": True},
                {"name": "status", "type": "enum", "values": ["ACTIVE", "CANCELLED"], "default": "ACTIVE"}]},
        ],
        "relationships": [
            {"name": "workshopBookings", "type": "one-to-many", "from": "Workshop", "to": "Booking",
             "onDelete": "CASCADE"},
            {"name": "roomBookings", "type": "one-to-many", "from": "Room", "to": "Booking", "onDelete": "CASCADE"},
        ],
        "operations": [*_crud("Workshop", "workshops"), *_crud("Room", "rooms"), *_crud("Booking", "bookings")],
        "rules": [
            {"id": "seatLimit", "kind": "capacity", "entity": "Booking",
             "params": {"parent": "workshopId", "capacityField": "capacity", "where": {"status": {"ne": "CANCELLED"}}}},
            {"id": "roomFree", "kind": "noOverlap", "entity": "Booking",
             "params": {"start": "startsAt", "end": "endsAt", "scope": ["roomId"],
                        "where": {"status": {"ne": "CANCELLED"}}}},
            {"id": "oncePerWorkshop", "kind": "uniqueTogether", "entity": "Booking",
             "params": {"fields": ["workshopId", "attendeeEmail"], "where": {"status": {"ne": "CANCELLED"}}}},
        ],
    }  # fmt: skip
    (tmp_path / "booking-spec.json").write_text(json.dumps(raw))
    return normalized(tmp_path / "booking-spec.json")


def _bookings(plan: dict) -> dict:
    return next(module for module in plan["modules"] if module["name"] == "bookings")


def test_the_three_kinds_are_planned_as_a_lock_a_constraint_and_an_index(tmp_path):
    spec = booking_spec(tmp_path)
    plan = build_plan(spec)
    assert plan["unresolved"] == [] and {"name": "rules", "version": "1"} in plan["plugins"]
    booking = next(m for m in plan["models"] if m["entity"] == "Booking")
    assert set(booking["constraintErrors"]) == {"ex_bookings_room_free", "uq_bookings_once_per_workshop"}
    model = database_files(plan)["src/modules/shared/infrastructure/models/booking_model.py"]
    assert (
        'ExcludeConstraint((column("room_id"), "="), (func.tstzrange(column("starts_at"), column("ends_at"), "[)"),'
        in model
    )
    assert "where=text(\"status <> 'CANCELLED'\")" in model
    assert 'Index("uq_bookings_once_per_workshop", "workshop_id", "attendee_email", unique=True' in model
    files = module_files(plan, spec, _bookings(plan))
    create = files["src/modules/bookings/usecases/create_booking_usecase.py"]
    assert "taken, capacity = self.booking_repo.workshop_taken(dto.workshop_id)" in create
    assert "ErrorCode.CAPACITY_REACHED" in create
    repository = files["src/modules/bookings/infrastructure/persistence/booking_repository.py"]
    assert ".with_for_update()" in repository and "!= BookingStatus.CANCELLED" in repository
    assert '"ex_bookings_room_free": {"code": ErrorCode.OVERLAP' in repository
    for relative, source in files.items():
        compile(source, relative, "exec")


def test_each_kind_has_a_concurrent_template_test(tmp_path):
    spec = booking_spec(tmp_path)
    plan = build_plan(spec)
    tests = module_tests(plan, spec, _bookings(plan))["tests/modules/bookings/test_booking_api.py"]
    for name in ("seat_limit", "room_free", "once_per_workshop"):
        assert f"def test_create_booking__{name}_concurrent(client):" in tests
    assert "with ThreadPoolExecutor(2) as pool:" in tests and "assert statuses == [201, 409]" in tests
    assert "parent = _seed_workshop(capacity=1)" in tests
    compile(tests, "tests", "exec")


def test_the_contract_carries_their_errors_and_scenarios_that_do_not_collide(tmp_path):
    spec = booking_spec(tmp_path)
    contract = build_contract(spec)
    create = contract_operations(contract)["booking.create"]["operation"]["x-bga"]
    codes = {(e["code"], tuple(e.get("fields", []))) for e in create["errors"]}
    assert ("CAPACITY_REACHED", ("workshopId",)) in codes and ("OVERLAP", ("roomId", "startsAt", "endsAt")) in codes
    names = [s["name"] for s in create["scenarios"]]
    assert names[-3:] == ["workshop full", "overlap", "duplicate"]
    success = next(s for s in create["scenarios"] if s["name"] == "success")
    full = next(s for s in create["scenarios"] if s["name"] == "workshop full")
    assert success["body"]["workshopId"] != full["body"]["workshopId"]
    rows = contract["x-bga"]["fixtures"]["Booking"]
    assert all(row["endsAt"] > row["startsAt"] for row in rows)  # real ranges, so a record can be overlapped


def test_concurrency_rules_are_validated():
    from src.modules.shared.domain.backend_spec.validator import validate_spec_data

    raw = json.loads(
        (tmp := Path(__file__).resolve().parents[2] / "examples" / "specs" / "two-entity.json").read_text()
    )
    raw["rules"] = [
        {"id": "a", "kind": "capacity", "entity": "Task", "params": {"parent": "title", "capacityField": "x"}},
        {"id": "b", "kind": "noOverlap", "entity": "Task", "params": {"start": "title", "end": "dueDate"}},
        {"id": "c", "kind": "uniqueTogether", "entity": "Task", "params": {"fields": ["title"],
                                                                             "where": {"status": {"ne": "LOST"}}}},
    ]  # fmt: skip
    assert tmp.name == "two-entity.json"
    paths = {issue.path for issue in validate_spec_data(raw).report.errors}
    assert {"/rules/0/params/parent", "/rules/1/params/start", "/rules/2/params/fields",
            "/rules/2/params/where/status"} <= paths  # fmt: skip


def test_a_status_rule_next_to_a_concurrency_rule_on_one_operation(tmp_path):
    """Story 22.8 (the soccer draft on Antigravity): a booking's status flow and its no-overlap rule both guard
    `booking.update`; the contract used to crash (`KeyError: 'path'`) adding the transition's scenarios."""
    booking_spec(tmp_path)
    raw = json.loads((tmp_path / "booking-spec.json").read_text())
    raw["entities"][2]["fields"][-1]["values"] = ["PENDING", "ACTIVE", "CANCELLED"]
    raw["entities"][2]["fields"][-1]["default"] = "PENDING"
    raw["rules"].append(
        {"id": "bookingFlow", "kind": "transition", "entity": "Booking",
         "params": {"field": "status", "transitions": {"PENDING": ["ACTIVE", "CANCELLED"], "ACTIVE": ["CANCELLED"]}}}
    )  # fmt: skip
    next(op for op in raw["operations"] if op["operationId"] == "booking.update")["rules"] = ["bookingFlow"]
    (tmp_path / "booking-spec.json").write_text(json.dumps(raw))
    spec = normalized(tmp_path / "booking-spec.json")
    update = contract_operations(build_contract(spec))["booking.update"]["operation"]["x-bga"]
    codes = {error["code"] for error in update["errors"]}
    assert {"INVALID_TRANSITION", "OVERLAP"} <= codes, codes
    assert any("transition" in scenario["name"] for scenario in update["scenarios"]), [
        s["name"] for s in update["scenarios"]
    ]
