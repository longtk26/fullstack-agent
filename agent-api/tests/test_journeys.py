"""Tests for Story 19.8: Journeys and domain operations."""

import copy
import json
from pathlib import Path
from typing import Any

from src.engines import PromptLibrary
from src.engines.fake_engine import FakeEngine, demo_scenario
from src.modules.shared.domain.backend_spec import validate_spec_data
from src.modules.shared.domain.frontend_spec import (
    FrontendIssueCode,
    add_manage_area,
    covered_operations,
    validate_frontend_spec_data,
)
from src.orchestrator.checks.consistency import check_spec_pair
from tests.workflow_helpers import cli_invocations, generation, run_job

EXAMPLES = Path(__file__).parents[2] / "examples"
C = FrontendIssueCode


def _minimal_frontend() -> dict[str, Any]:
    return {
        "specVersion": "1.0",
        "project": {"name": "Test Site", "mode": "dynamic"},
        "pages": [
            {
                "id": "home",
                "route": "/",
                "title": "Home",
                "sections": [
                    {
                        "id": "items-list",
                        "component": "CardGrid",
                        "data": {"operationId": "item.list", "fields": ["title"]},
                        "content": {
                            "actions": [
                                {
                                    "id": "publish",
                                    "label": "Publish",
                                    "kind": "mutation",
                                    "operationId": "item.publish",
                                }
                            ]
                        },
                    }
                ],
            },
            {
                "id": "create-page",
                "route": "/create",
                "title": "Create Item",
                "sections": [
                    {
                        "id": "item-form-section",
                        "component": "Form",
                        "form": "create_item_form",
                    }
                ],
            },
        ],
        "forms": [
            {
                "id": "create_item_form",
                "operationId": "item.create",
                "fields": [
                    {"name": "title", "type": "string", "required": True},
                    {"name": "score", "type": "integer"},
                ],
            }
        ],
    }


def _minimal_backend() -> dict[str, Any]:
    return {
        "specVersion": "1.0",
        "project": {"name": "Test App"},
        "stack": {"framework": "fastapi", "database": "postgresql", "orm": "sqlalchemy", "migration": "alembic"},
        "entities": [
            {
                "name": "Item",
                "fields": [
                    {"name": "id", "type": "uuid", "primary": True},
                    {"name": "title", "type": "string", "required": True},
                    {"name": "score", "type": "integer"},
                ],
            }
        ],
        "operations": [
            {
                "operationId": "item.list",
                "type": "crud",
                "action": "list",
                "entity": "Item",
                "method": "GET",
                "path": "/items",
            },
            {
                "operationId": "item.get",
                "type": "crud",
                "action": "get",
                "entity": "Item",
                "method": "GET",
                "path": "/items/{id}",
            },
            {
                "operationId": "item.create",
                "type": "crud",
                "action": "create",
                "entity": "Item",
                "method": "POST",
                "path": "/items",
            },
            {
                "operationId": "item.publish",
                "type": "custom",
                "entity": "Item",
                "method": "POST",
                "path": "/items/{id}/publish",
            },
        ],
    }


def test_journey_schema_and_validator_accepts_valid_steps_and_unique():
    fe = _minimal_frontend()
    fe["journeys"] = [
        {
            "id": "core-loop",
            "title": "Core Loop Journey",
            "goal": "Test browse, create and publish",
            "steps": [
                {"do": "visit", "page": "home"},
                {"do": "open", "section": "items-list", "record": "first"},
                {"do": "visit", "page": "create-page"},
                {
                    "do": "submit",
                    "section": "item-form-section",
                    "values": {"title": "item-$unique", "score": 42},
                },
                {"do": "action", "section": "items-list", "action": "publish", "record": "first"},
                {
                    "do": "expect",
                    "section": "items-list",
                    "text": "Published",
                    "count": 1,
                    "changed": {"field": "score", "record": "first"},
                    "live": True,
                },
            ],
        }
    ]

    res = validate_frontend_spec_data(fe)
    assert res.report.valid
    assert len(res.report.errors) == 0


def test_journey_validator_catches_unknown_references():
    fe = _minimal_frontend()
    fe["journeys"] = [
        {
            "id": "broken",
            "title": "Broken References",
            "steps": [
                {"do": "visit", "page": "non-existent-page"},
                {"do": "open", "section": "non-existent-section"},
                {
                    "do": "submit",
                    "section": "items-list",  # Not a form section
                    "values": {"title": "foo"},
                },
                {
                    "do": "submit",
                    "section": "item-form-section",
                    "values": {"unknownField": "bad"},  # Field not on create_item_form
                },
                {
                    "do": "action",
                    "section": "items-list",
                    "action": "non-existent-action",
                },
                {
                    "do": "expect",
                    "section": "items-list",
                    # No text, count, or changed
                },
            ],
        }
    ]

    res = validate_frontend_spec_data(fe)
    assert not res.report.valid
    codes = [issue.code for issue in res.report.errors]
    assert C.FE_UNKNOWN_PAGE in codes
    assert C.FE_UNKNOWN_SECTION in codes
    assert C.FE_UNKNOWN_FORM in codes
    assert C.FE_UNKNOWN_FIELD in codes
    assert C.FE_UNKNOWN_ACTION in codes
    assert C.FE_INVALID_JOURNEY_STEP in codes


def test_journey_duplicate_id():
    fe = _minimal_frontend()
    fe["journeys"] = [
        {"id": "study", "title": "First", "steps": [{"do": "visit", "page": "home"}]},
        {"id": "study", "title": "Second", "steps": [{"do": "visit", "page": "home"}]},
    ]
    res = validate_frontend_spec_data(fe)
    assert not res.report.valid
    assert any(i.code == C.FE_DUPLICATE_ID for i in res.report.errors)


def test_journey_operations_count_as_covered_and_pair_checked():
    fe = _minimal_frontend()
    be = _minimal_backend()

    # Add an uncovered custom operation
    be["operations"].append(
        {
            "operationId": "item.archive",
            "type": "custom",
            "entity": "Item",
            "method": "POST",
            "path": "/items/{id}/archive",
        }
    )

    # Before adding journey, item.archive is uncovered
    covered = covered_operations(fe)
    assert "item.archive" not in covered

    # Add a journey referencing item.archive
    fe["journeys"] = [
        {
            "id": "archive-flow",
            "title": "Archive Item",
            "steps": [
                {"do": "visit", "page": "home"},
                {"do": "action", "section": "items-list", "action": "publish", "operationId": "item.archive"},
            ],
        }
    ]

    covered_after = covered_operations(fe)
    assert "item.archive" in covered_after

    # Pair check with non-existent operation raises CONTRACT_UNKNOWN_OPERATION
    fe_bad = copy.deepcopy(fe)
    fe_bad["journeys"][0]["steps"].append(
        {"do": "action", "section": "items-list", "action": "publish", "operationId": "item.unknown"}
    )
    norm_fe = validate_frontend_spec_data(fe_bad).normalized
    norm_be = validate_spec_data(be).normalized
    issues = check_spec_pair(norm_fe, norm_be)
    assert any(i.code == C.CONTRACT_UNKNOWN_OPERATION for i in issues)


def test_golden_flashcards_pair_validates_cleanly():
    with open(EXAMPLES / "specs" / "flashcards.json") as f:
        be_raw = json.load(f)
    with open(EXAMPLES / "frontend-specs" / "flashcards-dynamic.json") as f:
        fe_raw = json.load(f)

    be_res = validate_spec_data(be_raw)
    assert be_res.report.valid, f"Backend errors: {be_res.report.errors}"

    fe_res = validate_frontend_spec_data(fe_raw)
    assert fe_res.report.valid, f"Frontend errors: {fe_res.report.errors}"

    # Pair consistency without manage area has 0 errors
    pair_issues = check_spec_pair(fe_res.normalized, be_res.normalized)
    errors = [i for i in pair_issues if i.severity.value == "error"]
    assert len(errors) == 0, f"Pair errors: {errors}"

    # With manage area, 0 warnings as well
    from src.orchestrator.contract import build_contract

    contract = build_contract(be_res.normalized)
    managed_fe, _ = add_manage_area(fe_res.normalized, contract)
    managed_issues = check_spec_pair(managed_fe, be_res.normalized)
    assert len(managed_issues) == 0, f"Manage area issues: {managed_issues}"


def test_prompt_snapshots_v7_and_complete_backend_v2():
    prompts = PromptLibrary()

    # Test draft_frontend_spec v7
    v7_rendered = prompts.render(
        "draft_frontend_spec",
        "v7",
        mode="dynamic",
        requirement_text="Vocabulary flashcards app with SM-2 scheduling",
        requirement_format="markdown",
        frontend_schema_path="frontend.json",
        frontend_schema_digest_path="frontend-digest.md",
        frontend_example_path="example-frontend.json",
        backend_schema_path="backend.json",
        backend_schema_digest_path="backend-digest.md",
        backend_example_path="example-backend.json",
        sections_path="sections.md",
        output_frontend_path="frontend-spec.json",
        output_backend_path="backend-spec.json",
        notes_path="notes.json",
        design_path=None,
        photos_enabled=False,
        max_photos=0,
    )
    assert "Journeys first" in v7_rendered.text
    assert "BackendSpec second" in v7_rendered.text
    assert "FrontendSpec screens third" in v7_rendered.text
    assert "Manage area" in v7_rendered.text
    assert "</untrusted-data>" in v7_rendered.text

    # Test complete_backend v2
    v2_rendered = prompts.render(
        "complete_backend",
        "v2",
        module={"name": "cards", "testFile": "tests/modules/cards/test_card_api.py"},
        module_json="{}",
        gaps=["card.review: custom operation"],
        generated_files=["src/modules/cards/presenter/router.py"],
        spec_path=".bga/spec.json",
        plan_path=".bga/plan.json",
        contract_path=".bga/contract.json",
        file_tree="src/",
        journeys=[
            {
                "id": "study",
                "title": "Study Due Cards",
                "goal": "Review cards",
                "steps": [{"do": "action", "section": "study-actions", "action": "good"}],
            }
        ],
    )
    assert "Journeys touching this module" in v2_rendered.text
    assert "Study Due Cards" in v2_rendered.text
    assert "tests/modules/cards/test_card_api.py" in v2_rendered.text


def test_fake_dynamic_generation_of_flashcards_completes(client, user_headers, tmp_path):
    with open(EXAMPLES / "specs" / "flashcards.json") as f:
        be_spec = json.load(f)
    with open(EXAMPLES / "frontend-specs" / "flashcards-dynamic.json") as f:
        fe_spec = json.load(f)

    response = client.post(
        "/api/v1/generations",
        json={
            "mode": "dynamic",
            "backendSpec": be_spec,
            "frontendSpec": fe_spec,
            "options": {"engine": "fake", "deployPreview": False, "crudFromTemplates": True},
        },
        headers=user_headers,
    )
    assert response.status_code == 202, response.text
    generation_id = response.json()["generationId"]
    engine = FakeEngine(tmp_path, demo_scenario(0))

    outcome = run_job(tmp_path, generation_id, engine=engine)
    assert outcome == "COMPLETED_WITH_WARNINGS"

    gen = generation(generation_id)
    assert gen.lanes == {"backend": "COMPLETED", "frontend": "COMPLETED", "integration": "SKIPPED"}

    # Check complete_backend invocations
    purposes = [c.purpose for c in cli_invocations(generation_id)]
    assert "complete_backend" in purposes

    # Check that custom review card usecase and tests were written
    project = tmp_path / generation_id / "project"
    review_usecase = project / "src/modules/cards/usecases/review_card_usecase.py"
    assert review_usecase.exists()
    assert "SM-2" in review_usecase.read_text() or "ReviewLog" in review_usecase.read_text()

    review_test = project / "tests/modules/cards/test_card_review_api.py"
    assert review_test.exists()
