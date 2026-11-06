"""Date-range lists (Story 23.4): a list operation's `ranges` become `<field>From` / `<field>To` query parameters
(inclusive) in the backend, the contract and the mocks; code adds them when a calendar or an agenda needs them."""

import ast
import copy
import json
from pathlib import Path

from src.modules.shared.domain.backend_spec import validate_spec_data
from src.orchestrator.backend.codegen import module_files, module_tests
from src.orchestrator.backend.planner import build_plan
from src.orchestrator.frontend.app.design import list_features
from src.orchestrator.frontend.codegen import mock_operations
from src.orchestrator.integration.contract import build_contract

EXAMPLES = Path(__file__).parents[2] / "examples"


def _clinic(ranges: list[str]) -> dict:
    spec = json.loads((EXAMPLES / "specs" / "clinic-bookings.json").read_text())
    for op in spec["operations"]:
        if op["operationId"] == "appointment.list":
            op["ranges"] = ranges
    return spec


def _date_field(spec: dict) -> str:
    appointment = next(e for e in spec["entities"] if e["name"] == "Appointment")
    return next(
        f["name"] for f in appointment["fields"] if f["type"] in ("date", "datetime") and f["name"] != "createdAt"
    )


def test_ranges_are_dates_of_a_list():
    spec = _clinic([])
    day = _date_field(spec)
    assert validate_spec_data(_clinic([day])).report.valid
    bad = _clinic(["status"])
    errors = [issue.message for issue in validate_spec_data(bad).report.errors]
    assert any("needs a date or datetime field" in message for message in errors)
    ghost = _clinic(["nowhere"])
    assert any("no field 'nowhere'" in issue.message for issue in validate_spec_data(ghost).report.errors)


def test_the_backend_contract_and_mocks_take_the_bounds():
    spec = validate_spec_data(_clinic([_date_field(_clinic([]))])).normalized
    day = _date_field(spec)
    plan = build_plan(spec)
    module = next(m for m in plan["modules"] if any(op["operationId"] == "appointment.list" for op in m["operations"]))
    op = next(op for op in module["operations"] if op["operationId"] == "appointment.list")
    assert [r["param"] for r in op["ranges"]] == [day]
    assert any("__range_" in t["id"] for t in module["tests"])

    files = module_files(plan, spec, module) | module_tests(plan, spec, module)
    joined = "\n".join(files.values())
    assert f'alias="{day}From"' in joined and f'alias="{day}To"' in joined, "the router's query parameters"
    assert '__gte"' in joined and '__lte"' in joined, "the use case passes the bounds as filters"
    repository = next(
        text for path, text in files.items() if path.endswith("_repository.py") and "infrastructure" in path
    )
    assert 'attribute.partition("__")' in repository and "column >= value" in repository
    for path, text in files.items():
        if path.endswith(".py") and text.strip():
            ast.parse(text)
    assert any(f'"{day}From"' in text and "early" in text for path, text in files.items() if "test" in path)

    contract = build_contract(spec, plan)
    params = {p["name"]: p for p in contract["paths"]["/appointments"]["get"]["parameters"]}
    assert params[f"{day}From"]["schema"]["format"] in ("date", "date-time") and f"{day}To" in params
    mock = next(m for m in mock_operations(contract) if m["operationId"] == "appointment.list")
    assert mock["ranges"] == {f"{day}From": {"field": day, "bound": "gte"}, f"{day}To": {"field": day, "bound": "lte"}}
    assert f"{day}From" not in mock["filters"]


def test_a_module_without_ranges_is_generated_as_before():
    spec = validate_spec_data(_clinic([])).normalized
    plan = build_plan(spec)
    for module in [m for m in plan["modules"] if m.get("entity")]:
        for text in module_files(plan, spec, module).values():
            assert 'partition("__")' not in text


def test_code_adds_a_range_and_a_sort_for_a_calendar_and_a_sort_for_a_feed():
    clinic = validate_spec_data(_clinic([])).normalized
    day = _date_field(clinic)
    outline = {"design": {"entities": {"Appointment": {"view": "calendar", "dateField": day, "roles": {}}}}}
    operations, notes = list_features(clinic, copy.deepcopy(clinic["operations"]), outline)
    listed = next(op for op in operations if op["operationId"] == "appointment.list")
    assert listed["ranges"] == [day] and day in listed["sort"]
    assert any("for its calendar view" in note["message"] for note in notes)

    news = validate_spec_data(json.loads((EXAMPLES / "specs" / "news-feed.json").read_text())).normalized
    feed = {"design": {"entities": {"Post": {"view": "feed", "roles": {"meta": ["publishedAt"]}}}}}
    operations, _ = list_features(news, copy.deepcopy(news["operations"]), feed)
    posts = next(op for op in operations if op["operationId"] == "post.list")
    assert "publishedAt" in posts["sort"]


def test_an_areas_calendar_counts_too():
    clinic = validate_spec_data(_clinic([])).normalized
    day = _date_field(clinic)
    outline = {
        "design": {"entities": {}},
        "areas": [{"id": "desk", "design": {"entities": {"Appointment": {"view": "calendar", "dateField": day}}}}],
    }
    operations, _ = list_features(clinic, copy.deepcopy(clinic["operations"]), outline)
    assert next(op for op in operations if op["operationId"] == "appointment.list")["ranges"] == [day]
