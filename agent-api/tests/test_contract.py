"""API contract (Story 12.3): deterministic OpenAPI 3.1 from the plan, and schema conformance of generated apps."""

import copy
import json
import os
from pathlib import Path

import pytest
from generation_helpers import EXAMPLES, normalized

from src.orchestrator.checks.conformance import compare_contract
from src.orchestrator.contract import build_contract, contract_operations, dump_contract, resolve
from src.orchestrator.planner import build_plan, planned_operations

SNAPSHOTS = Path(__file__).parent / "fixtures" / "contracts"
OPENAPI = Path(__file__).parent / "fixtures" / "openapi"
SPECS = ("two-entity", "task-management", "shop")


def contract(name: str) -> dict:
    return build_contract(normalized(EXAMPLES / "specs" / f"{name}.json"))


@pytest.mark.parametrize("name", SPECS)
def test_contract_matches_snapshot_byte_for_byte(name):
    text = dump_contract(contract(name))
    assert text == dump_contract(contract(name))
    snapshot = SNAPSHOTS / f"{name}.contract.json"
    if os.environ.get("UPDATE_SNAPSHOTS") or not snapshot.exists():
        snapshot.write_text(text)
    assert text == snapshot.read_text(), "contract changed: review, then rerun with UPDATE_SNAPSHOTS=1"


@pytest.mark.parametrize("name", SPECS)
def test_every_planned_operation_is_in_the_contract(name):
    spec = normalized(EXAMPLES / "specs" / f"{name}.json")
    document = build_contract(spec)
    found = {(op["method"], op["path"], operation_id) for operation_id, op in contract_operations(document).items()}
    assert found == planned_operations(build_plan(spec))
    assert document["openapi"] == "3.1.0"


def test_list_operations_have_the_envelope_and_query_parameters():
    document = contract("shop")
    operation = contract_operations(document)["product.list"]["operation"]
    params = {(p["in"], p["name"]): p for p in operation["parameters"]}
    assert set(params) == {("query", n) for n in ("limit", "offset", "categoryId", "sort", "q")}
    assert params[("query", "limit")]["schema"] == {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}
    assert params[("query", "sort")]["schema"]["enum"] == [
        "name",
        "-name",
        "price",
        "-price",
        "createdAt",
        "-createdAt",
    ]
    assert params[("query", "categoryId")]["schema"] == {"type": "string", "format": "uuid"}
    envelope = resolve(document, operation["responses"]["200"]["content"]["application/json"]["schema"])
    assert envelope["required"] == ["items", "total", "limit", "offset"]
    item = resolve(document, envelope["properties"]["items"]["items"])
    assert item["properties"]["price"] == {"type": ["number", "string"], "format": "decimal", "minimum": 0}
    assert item["properties"]["description"]["type"] == ["string", "null"]


def test_requests_responses_and_errors():
    document = contract("two-entity")
    operations = contract_operations(document)
    create = operations["task.create"]["operation"]
    body = resolve(document, create["requestBody"]["content"]["application/json"]["schema"])
    assert body["required"] == ["projectId", "title"]
    assert "id" not in body["properties"]  # generated keys are not sent
    assert body["properties"]["status"]["default"] == "TODO"
    assert set(create["responses"]) == {"201", "400", "422"}
    error = create["responses"]["400"]
    assert error["description"] == "REFERENCE_NOT_FOUND"
    envelope = resolve(document, error["content"]["application/json"]["schema"])
    assert envelope["properties"]["error"]["required"] == ["code", "message"]
    update = resolve(
        document, operations["task.update"]["operation"]["requestBody"]["content"]["application/json"]["schema"]
    )
    assert "required" not in update  # partial update
    assert operations["task.delete"]["operation"]["responses"]["204"] == {"description": "No content"}
    project_create = resolve(
        document, operations["project.create"]["operation"]["requestBody"]["content"]["application/json"]["schema"]
    )
    assert set(project_create["properties"]) == {"name", "description"}  # createdAt defaults to now
    assert "409" in operations["project.create"]["operation"]["responses"]


def test_examples_come_from_the_seed_with_consistent_foreign_keys():
    document = contract("shop")
    fixtures = document["x-bga"]["fixtures"]
    products, categories = fixtures["Product"], fixtures["Category"]
    assert [p["name"] for p in products] == ["House blend, 250 g", "Single origin Ethiopia, 250 g", "Sencha, 100 g"]
    assert {p["categoryId"] for p in products} <= {c["id"] for c in categories}
    assert all(p["createdAt"] == "2026-01-01T09:00:00Z" and p["imageUrl"] is None for p in products)
    listing = contract_operations(document)["product.list"]["operation"]["responses"]["200"]["content"]
    example = listing["application/json"]["examples"]["seed"]["value"]
    assert example["total"] == 3 and example["items"][0]["price"] == 9.5
    # no seed: three synthesized records, children point at synthesized parents
    cart = fixtures["CartItem"]
    assert len(cart) == 3 and {item["productId"] for item in cart} <= {p["id"] for p in products}
    assert (
        "synthesized"
        in contract_operations(document)["cartItem.list"]["operation"]["responses"]["200"]["content"][
            "application/json"
        ]["examples"]
    )


def test_synthesized_examples_respect_types_and_bounds():
    fixtures = contract("two-entity")["x-bga"]["fixtures"]
    tasks = fixtures["Task"]
    assert [task["status"] for task in tasks] == ["TODO", "IN_PROGRESS", "DONE"]
    assert all(1 <= task["priority"] <= 5 for task in tasks)
    assert {task["projectId"] for task in tasks} == {project["id"] for project in fixtures["Project"]}


# -- conformance -------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("source", ["golden", "engine"])
def test_generated_two_entity_apps_conform(source):
    """Real exports: the golden project (fake engine) and an engine-generated backend of the same spec."""
    document = json.loads((OPENAPI / f"two-entity.{source}.json").read_text())
    assert compare_contract(contract("two-entity"), document) == []


def _golden() -> dict:
    return json.loads((OPENAPI / "two-entity.golden.json").read_text())


def _schemas(document: dict) -> dict:
    return document["components"]["schemas"]


MUTATIONS = [
    ("missing response field", lambda d: _schemas(d)["TaskResponseDto"]["properties"].pop("dueDate"),
     "GET /tasks/{id}", "response 200.dueDate: missing"),
    ("wrong response type", lambda d: _schemas(d)["TaskResponseDto"]["properties"].update(priority={"type": "string"}),
     "GET /tasks/{id}", "response 200.priority: the app returns string"),
    ("required field made optional", lambda d: _schemas(d)["CreateTaskRequestDto"]["required"].remove("title"),
     "POST /tasks", "body.title: optional in the app, required in the contract"),
    ("extra required field", lambda d: _schemas(d)["CreateTaskRequestDto"]["required"].append("dueDate"),
     "POST /tasks", "body.dueDate: required in the app, optional in the contract"),
    ("enum drift", lambda d: _schemas(d)["TaskStatus"].update(enum=["TODO", "DONE", "ARCHIVED"]),
     "POST /tasks", "body.status: enum values differ (IN_PROGRESS)"),
    ("required query parameter", lambda d: [
        p.update(required=True) for p in d["paths"]["/tasks"]["get"]["parameters"] if p["name"] == "limit"
     ], "GET /tasks", "query parameter 'limit': required=True"),
    ("missing filter", lambda d: d["paths"]["/tasks"]["get"].update(
        parameters=[p for p in d["paths"]["/tasks"]["get"]["parameters"] if p["name"] != "status"]
     ), "GET /tasks", "query parameter 'status': missing"),
    ("status code", lambda d: d["paths"]["/tasks"]["post"]["responses"].update(
        {"200": d["paths"]["/tasks"]["post"]["responses"].pop("201")}
     ), "POST /tasks", "response 201: not declared by the app"),
    ("undeclared error status", lambda d: d["paths"]["/tasks/{id}"]["get"]["responses"].pop("404"),
     "GET /tasks/{id}", "response 404: not declared by the app"),
    ("path parameter type", lambda d: [
        p.update(schema={"type": "integer"}) for p in d["paths"]["/tasks/{id}"]["get"]["parameters"]
     ], "GET /tasks/{id}", "path parameter 'id': the contract allows string, the app accepts integer"),
]  # fmt: skip


@pytest.mark.parametrize(("label", "change", "operation", "message"), MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_conformance_reports_each_kind_of_drift(label, change, operation, message):
    document = copy.deepcopy(_golden())
    change(document)
    problems = compare_contract(contract("two-entity"), document)
    assert any(p["operation"] == operation and p["message"].startswith(message) for p in problems), problems


def test_custom_operation_mock_plans():
    """Story 19.5: every custom operation gets a mock plan in x-bga.mock."""
    from src.orchestrator.frontend_codegen import mock_operations

    base_spec = normalized(EXAMPLES / "specs" / "two-entity.json")
    spec = copy.deepcopy(base_spec)
    spec["operations"].extend(
        [
            # 1. merge: POST/PATCH with id returning entity
            {
                "operationId": "task.complete",
                "type": "custom",
                "entity": "Task",
                "method": "POST",
                "path": "/tasks/{id}/complete",
                "response": {"entity": "Task"},
            },
            # 2. record: GET with id returning entity
            {
                "operationId": "task.summary",
                "type": "custom",
                "entity": "Task",
                "method": "GET",
                "path": "/tasks/{id}/summary",
                "response": {"entity": "Task"},
            },
            # 3. records: GET without id returning entity
            {
                "operationId": "task.due",
                "type": "custom",
                "entity": "Task",
                "method": "GET",
                "path": "/tasks/due",
                "response": {"entity": "Task"},
            },
            # 4. create: POST without id returning entity
            {
                "operationId": "task.quickCreate",
                "type": "custom",
                "entity": "Task",
                "method": "POST",
                "path": "/tasks/quick",
                "response": {"entity": "Task"},
            },
            # 5. sample: anything else (e.g. custom properties schema)
            {
                "operationId": "task.stats",
                "type": "custom",
                "entity": "Task",
                "method": "GET",
                "path": "/tasks/stats",
                "response": {
                    "properties": [
                        {"name": "totalCount", "type": "integer"},
                        {"name": "completionRate", "type": "float"},
                    ]
                },
            },
        ]
    )
    doc = build_contract(spec)
    ops = contract_operations(doc)

    assert ops["task.complete"]["operation"]["x-bga"]["mock"] == "merge"
    assert ops["task.summary"]["operation"]["x-bga"]["mock"] == "record"
    assert ops["task.due"]["operation"]["x-bga"]["mock"] == "records"
    assert ops["task.quickCreate"]["operation"]["x-bga"]["mock"] == "create"
    assert ops["task.stats"]["operation"]["x-bga"]["mock"] == "sample"

    sample = ops["task.stats"]["operation"]["x-bga"]["sample"]
    assert "totalCount" in sample and isinstance(sample["totalCount"], int)
    assert "completionRate" in sample and isinstance(sample["completionRate"], float)

    # Verify mock_operations carries mock and sample
    mocked = {m["operationId"]: m for m in mock_operations(doc)}
    assert mocked["task.complete"]["mock"] == "merge"
    assert mocked["task.summary"]["mock"] == "record"
    assert mocked["task.due"]["mock"] == "records"
    assert mocked["task.quickCreate"]["mock"] == "create"
    assert mocked["task.stats"]["mock"] == "sample"
    assert mocked["task.stats"]["sample"] == sample

