"""The integration contract (Story 10.0b): field sources, parent summaries, allowed actions, errors and scenarios, in
the contract, the generated backend, the mocks and the pair check."""

import json
from pathlib import Path

from src.modules.shared.domain.backend_spec import validate_spec_text
from src.modules.shared.domain.frontend_spec import FrontendIssueCode
from src.orchestrator.backend.codegen import database_files, module_files
from src.orchestrator.backend.planner import build_plan
from src.orchestrator.checks.consistency import check_spec_pair, reconcile_spec_pair
from src.orchestrator.checks.smoke import judge, scenario_calls, smoke_calls
from src.orchestrator.frontend.codegen import types_ts
from src.orchestrator.integration.contract import (
    UNKNOWN_ID,
    build_contract,
    contract_operations,
    presented_record,
)
from tests.generation_helpers import normalized

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
OVERLAY = Path(__file__).resolve().parents[1] / "templates" / "nextjs_overlay" / "files"


def _spec(name: str) -> dict:
    return normalized(EXAMPLES / "specs" / f"{name}.json")


def _operation(contract: dict, operation_id: str) -> dict:
    return contract_operations(contract)[operation_id]["operation"]


# -- planner ---------------------------------------------------------------------------------------------------------


def test_labels_references_and_record_actions_are_planned():
    plan = build_plan(_spec("flashcards"))
    models = {model["entity"]: model for model in plan["models"] if model.get("entity")}
    assert models["Deck"]["label"] == {"attr": "name", "apiName": "name"}
    assert models["Card"]["label"]["apiName"] == "front"  # no usual name: the first required string
    [deck] = models["Card"]["references"]
    assert (deck["field"], deck["apiName"], deck["entity"], deck["labelField"]) == ("deckId", "deck", "Deck", "name")
    cards = next(module for module in plan["modules"] if module["name"] == "cards")
    assert cards["recordActions"] == ["update", "delete", "card.review"]  # `POST /cards/{id}/review` acts on one card
    assert "references" in cards["port"]["methods"]


def test_display_field_names_the_label_and_must_exist(tmp_path):
    spec = json.loads((EXAMPLES / "specs" / "flashcards.json").read_text())
    card = next(entity for entity in spec["entities"] if entity["name"] == "Card")
    card["displayField"] = "back"
    result = validate_spec_text(json.dumps(spec))
    assert result.report.valid
    card_model = next(m for m in build_plan(result.normalized)["models"] if m.get("entity") == "Card")
    assert card_model["label"]["apiName"] == "back"

    card["displayField"] = "nope"
    report = validate_spec_text(json.dumps(spec)).report
    assert [(e.code, e.path) for e in report.errors] == [("UNKNOWN_FIELD_REF", "/entities/1/displayField")]


# -- contract --------------------------------------------------------------------------------------------------------


def test_request_fields_say_where_their_values_come_from():
    contract = build_contract(_spec("flashcards"))
    properties = contract["components"]["schemas"]["CreateCardRequest"]["properties"]
    assert properties["deckId"]["x-bga"] == {
        "source": "reference",
        "ref": {"entity": "Deck", "listOperation": "deck.list", "detailOperation": "deck.get", "labelField": "name"},
    }
    assert properties["front"]["x-bga"] == {"source": "input"}
    assert all("x-bga" in schema for schema in properties.values())


def test_records_carry_parent_summaries_and_allowed_actions():
    contract = build_contract(_spec("flashcards"))
    card = contract["components"]["schemas"]["CardResponse"]
    assert card["properties"]["deck"] == {"anyOf": [{"$ref": "#/components/schemas/DeckSummary"}, {"type": "null"}]}
    assert card["properties"]["allowedActions"]["items"]["enum"] == ["update", "delete", "card.review"]
    assert {"deck", "allowedActions"} <= set(card["required"])
    example = _operation(contract, "card.get")["responses"]["200"]["content"]["application/json"]["examples"]
    record = next(iter(example.values()))["value"]
    assert record["deck"] == {"id": record["deckId"], "label": "Spanish Basics"}
    assert record["allowedActions"] == ["update", "delete", "card.review"]
    # the mocks read the same from `x-bga.entities`
    raw = contract["x-bga"]["fixtures"]["Card"][0]
    assert presented_record(contract, "Card", raw) == record
    assert "deck: TDeckSummary | null;" in types_ts(contract)


def test_operations_list_their_errors_with_the_fields_to_mark():
    contract = build_contract(_spec("two-entity"))
    errors = _operation(contract, "project.create")["x-bga"]["errors"]
    conflict = next(error for error in errors if error["code"] == "CONFLICT")
    assert conflict == {
        "status": 409,
        "code": "CONFLICT",
        "message": "A project with this name already exists",
        "fields": ["name"],
    }
    task_errors = _operation(contract, "task.create")["x-bga"]["errors"]
    assert {"status": 400, "code": "REFERENCE_NOT_FOUND", "message": "A referenced record does not exist",
            "fields": ["projectId"]} in task_errors  # fmt: skip


# -- generated backend -----------------------------------------------------------------------------------------------


def test_the_backend_presents_records_as_the_contract_says():
    spec = _spec("flashcards")
    plan = build_plan(spec)
    cards = next(module for module in plan["modules"] if module["name"] == "cards")
    files = module_files(plan, spec, cards)
    dto = files["src/modules/cards/presenter/dtos/card_response_dto.py"]
    assert 'ALLOWED_ACTIONS: tuple[str, ...] = ("update", "delete", "card.review")' in dto
    assert "deck: DeckSummaryDto | None" in dto and "allowed_actions: list[str]" in dto
    repository = files["src/modules/cards/infrastructure/persistence/card_repository.py"]
    assert "def references(self, records: list[CardEntity]) -> References:" in repository
    assert "col(DeckModel.id).in_(deck_ids)" in repository  # one query per page, not per row
    listed = files["src/modules/cards/usecases/list_cards_usecase.py"]
    assert "references = self.card_repo.references(cards)" in listed
    assert "class DeckSummaryDto(BaseModel):" in database_files(plan)["src/modules/shared/presenter/summaries.py"]
    for source in [*files.values(), *database_files(plan).values()]:
        compile(source, "generated.py", "exec")


def test_unique_conflicts_name_their_fields():
    spec = _spec("two-entity")
    plan = build_plan(spec)
    projects = next(module for module in plan["modules"] if module["name"] == "projects")
    repository = module_files(plan, spec, projects)[
        "src/modules/projects/infrastructure/persistence/project_repository.py"
    ]
    assert 'details={"fields": ["name"]}' in repository


# -- scenarios -------------------------------------------------------------------------------------------------------


def test_scenarios_cover_success_and_each_planned_error():
    contract = build_contract(_spec("two-entity"))
    names = {
        op_id: [s["name"] for s in (found["operation"]["x-bga"].get("scenarios") or [])]
        for op_id, found in contract_operations(contract).items()
    }
    assert names["project.create"] == ["success", "missing required field", "duplicate name"]
    assert names["task.create"] == ["success", "missing required field", "unknown projectId"]
    assert names["task.get"] == ["success", "unknown id"]
    create = _operation(contract, "project.create")["x-bga"]["scenarios"]
    assert create[0]["body"]["name"] != contract["x-bga"]["fixtures"]["Project"][0]["name"]  # not a duplicate
    assert create[2]["body"]["name"] == contract["x-bga"]["fixtures"]["Project"][0]["name"]
    unknown = _operation(contract, "task.get")["x-bga"]["scenarios"][1]
    assert unknown["params"] == {"id": UNKNOWN_ID} and unknown["expect"] == {"status": 404, "code": "NOT_FOUND"}


def _answer(status: int, body) -> dict:
    return {"status": status, "body": json.dumps(body)}


def test_the_smoke_check_requires_each_scenarios_status_and_code():
    contract = build_contract(_spec("two-entity"))
    calls, _ = scenario_calls(contract)
    project = presented_record(contract, "Project", contract["x-bga"]["fixtures"]["Project"][0])
    task = presented_record(contract, "Task", contract["x-bga"]["fixtures"]["Task"][0])
    page = {"items": [], "total": 0, "limit": 20, "offset": 0}

    def right(call: dict) -> dict:
        want = call["expect"]
        if want.get("code"):
            return _answer(want["status"], {"error": {"code": want["code"], "message": "x", "details": None}})
        if want["status"] == 204:
            return {"status": 204, "body": ""}
        if call["operationId"].endswith(".list"):
            return _answer(200, page)
        return _answer(want["status"], project if call["operationId"].startswith("project") else task)

    assert judge(contract, calls, [right(call) for call in calls]) == []

    # a planted mismatch: the duplicate is accepted
    duplicate = next(i for i, call in enumerate(calls) if call["scenario"] == "duplicate name")
    answers = [right(call) for call in calls]
    answers[duplicate] = _answer(201, project)
    [problem] = judge(contract, calls, answers)
    assert problem["message"] == "project.create (duplicate name): expected 409 CONFLICT, got 201"
    # a wrong code is a mismatch too, even with the right status
    answers[duplicate] = _answer(409, {"error": {"code": "VALIDATION_ERROR", "message": "x"}})
    assert "got 409 VALIDATION_ERROR" in judge(contract, calls, answers)[0]["message"]
    # and so is a record without what the contract adds to it
    success = next(i for i, call in enumerate(calls) if call["operationId"] == "project.get")
    answers = [right(call) for call in calls]
    answers[success] = _answer(200, contract["x-bga"]["fixtures"]["Project"][0])
    assert any("allowedActions" in problem["message"] for problem in judge(contract, calls, answers))


def test_smoke_calls_run_the_scenarios_before_the_custom_operations():
    spec = _spec("flashcards")
    contract, plan = build_contract(spec), build_plan(spec)
    calls, _ = smoke_calls(contract, plan)
    scenarios = [call for call in calls if call.get("expect")]
    custom = [call for call in calls if not call.get("expect")]
    assert scenarios and custom and calls == scenarios + custom
    assert {call["operationId"] for call in custom} == {"card.listDue", "card.review", "deck.stats"}


# -- the pair check and the mocks ------------------------------------------------------------------------------------


def _frontend(name: str) -> dict:
    return json.loads((EXAMPLES / "frontend-specs" / f"{name}.json").read_text())


def test_a_form_that_asks_for_an_id_is_flagged():
    backend = _spec("flashcards")
    issues = check_spec_pair(_frontend("flashcards-dynamic"), backend)
    [issue] = [issue for issue in issues if issue.code == FrontendIssueCode.FE_FIELD_SOURCE]
    assert issue.severity == "warning"  # no picker before the app kit (22.6): the draft is not rejected
    assert issue.message == "Form field 'deckId' asks the user to type a Deck id"
    assert "$route.id" in issue.hint


def test_a_form_on_the_parents_page_takes_the_parent_from_the_route():
    backend = _spec("flashcards")
    frontend = _frontend("flashcards-dynamic")
    detail = next(page for page in frontend["pages"] if page["id"] == "deck-detail")
    detail["sections"].append({"id": "add-card", "component": "Form", "form": "new_card_form"})
    frontend["pages"] = [page for page in frontend["pages"] if page["id"] != "card-new"]  # only on the deck's page
    frontend["layout"]["header"]["navigation"] = [
        link for link in frontend["layout"]["header"]["navigation"] if link.get("page") != "card-new"
    ]
    healed, notes = reconcile_spec_pair(frontend, backend)
    field = next(f for f in healed["forms"][0]["fields"] if f["name"] == "deckId")
    assert field["hidden"] is True and field["value"] == "$route.id"
    assert any("takes the Deck from the page ($route.id)" in note["message"] for note in notes)
    assert not [issue for issue in check_spec_pair(healed, backend) if issue.code == FrontendIssueCode.FE_FIELD_SOURCE]


def test_a_form_shown_where_the_parent_is_unknown_keeps_its_field():
    backend = _spec("flashcards")
    healed, _ = reconcile_spec_pair(_frontend("flashcards-dynamic"), backend)  # on `/cards/new`: no deck in the route
    field = next(f for f in healed["forms"][0]["fields"] if f["name"] == "deckId")
    assert not field.get("hidden") and field.get("value") is None


def test_the_mocks_present_records_like_the_backend():
    handlers = (OVERLAY / "dynamic" / "src" / "mocks" / "handlers.ts").read_text()
    assert 'import entities from "./entities.json";' in handlers
    assert "present(op.entity, found)" in handlers and "present(op.entity, created)" in handlers
    assert ".map((item) => present(op.entity, item))" in handlers
