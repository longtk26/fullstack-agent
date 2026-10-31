import json
import os
from pathlib import Path

from src.orchestrator.contract import build_contract
from src.orchestrator.frontend_codegen import generated_files, journeys_spec
from src.orchestrator.frontend_planner import plan_frontend
from src.orchestrator.planner import build_plan
from tests.generation_helpers import normalized

REPO = Path(__file__).resolve().parents[2]
EXAMPLES = REPO / "examples"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
SNAPSHOTS = FIXTURES / "snapshots"


def _plan_flashcards():
    be_spec = normalized(EXAMPLES / "specs" / "flashcards.json")
    fe_spec = json.loads((EXAMPLES / "frontend-specs" / "flashcards-dynamic.json").read_text())
    be_plan = build_plan(be_spec)
    contract = build_contract(be_spec, be_plan)
    fe_plan = plan_frontend(fe_spec, contract)
    return fe_plan, fe_spec, contract


def test_flashcards_journeys_spec_snapshot():
    fe_plan, fe_spec, contract = _plan_flashcards()
    spec_text = journeys_spec(fe_plan, fe_spec, contract)
    assert spec_text is not None

    snapshot = SNAPSHOTS / "flashcards.journeys.spec.ts"
    if os.environ.get("UPDATE_SNAPSHOTS") or not snapshot.exists():
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_text(spec_text)

    assert spec_text == snapshot.read_text(), (
        "Generated journeys.spec.ts changed: review, then rerun with UPDATE_SNAPSHOTS=1"
    )


def test_journeys_spec_omitted_when_no_journeys():
    fe_plan, fe_spec, contract = _plan_flashcards()
    fe_spec_no_journeys = {**fe_spec, "journeys": []}
    assert journeys_spec(fe_plan, fe_spec_no_journeys, contract) is None

    files = generated_files(fe_plan, fe_spec_no_journeys, contract)
    assert "tests/e2e/journeys.spec.ts" not in files


def test_journey_step_visit():
    plan = {
        "routes": [{"pageId": "home", "route": "/"}],
        "tests": [{"kind": "route", "pageId": "home", "path": "/"}],
    }
    spec = {
        "journeys": [
            {
                "id": "j_visit",
                "title": "Visit Journey",
                "steps": [{"do": "visit", "page": "home"}],
            }
        ]
    }
    code = journeys_spec(plan, spec, None)
    assert code is not None
    assert 'test("j_visit: Visit Journey"' in code
    assert 'await test.step("j_visit: 0 visit"' in code
    assert 'await page.goto("/");' in code
    assert 'await page.waitForLoadState("domcontentloaded");' in code


def test_journey_step_open():
    plan = {
        "routes": [{"pageId": "home", "route": "/"}],
        "tests": [],
    }
    spec = {
        "journeys": [
            {
                "id": "j_open",
                "title": "Open Journey",
                "steps": [
                    {"do": "open", "section": "items-grid", "record": "first"},
                    {"do": "open", "section": "items-grid", "record": "custom-id-123"},
                ],
            }
        ]
    }
    code = journeys_spec(plan, spec, None)
    assert code is not None
    assert 'sec.locator("[data-bga-record]").first()' in code
    assert 'sec.locator("[data-bga-record=\\"custom-id-123\\"]")' in code
    assert 'await rec.locator("a").first().click();' in code


def test_journey_step_submit():
    plan = {
        "routes": [
            {
                "pageId": "create",
                "route": "/create",
                "sections": [{"id": "form-sec", "form": "test-form"}],
            }
        ],
        "forms": [
            {
                "id": "test-form",
                "onSuccess": {"toast": "Item created", "navigate": "/items"},
            }
        ],
        "tests": [],
    }
    spec = {
        "journeys": [
            {
                "id": "j_submit",
                "title": "Submit Journey",
                "steps": [
                    {
                        "do": "submit",
                        "section": "form-sec",
                        "values": {
                            "name": "item-$unique",
                            "active": True,
                            "count": 5,
                        },
                    }
                ],
            }
        ]
    }
    code = journeys_spec(plan, spec, None)
    assert code is not None
    assert 'sec.locator("[name=\\"name\\"]").first().fill("item-$unique".replace("$unique", unique))' in code
    assert 'sec.locator("[name=\\"active\\"]").first().setChecked(true)' in code
    assert 'sec.locator("[name=\\"count\\"]").first().fill(String(5))' in code
    assert "sec.locator('button[type=\"submit\"]').first().click()" in code
    assert 'await expect(page.getByText("Item created").filter({ visible: true }).first()).toBeVisible()' in code


def test_journey_step_action():
    plan = {"routes": [], "tests": []}
    spec = {
        "journeys": [
            {
                "id": "j_action",
                "title": "Action Journey",
                "steps": [
                    {"do": "action", "section": "btn-bar", "action": "delete-item", "record": "item-1"},
                ],
            }
        ]
    }
    code = journeys_spec(plan, spec, None)
    assert code is not None
    assert 'data-bga-action=\\"delete-item\\"' in code
    assert 'page.once("dialog"' in code
    assert "await actionBtn.click()" in code
    assert 'page.getByRole("button", { name: /confirm|proceed|ok|yes/i })' in code


def test_journey_step_expect_text_and_count():
    plan = {"routes": [], "tests": []}
    spec = {
        "journeys": [
            {
                "id": "j_expect",
                "title": "Expect Journey",
                "steps": [
                    {"do": "expect", "section": "list-sec", "text": "Welcome-$unique"},
                    {"do": "expect", "section": "list-sec", "count": 3},
                ],
            }
        ]
    }
    code = journeys_spec(plan, spec, None)
    assert code is not None
    assert (
        'await expect(page.getByText("Welcome-$unique".replace("$unique", unique))'
        ".filter({ visible: true }).first()).toBeVisible()" in code
    )
    assert 'await expect(sec.locator("[data-bga-record]")).toHaveCount(3)' in code


def test_journey_step_expect_changed_and_live_skip():
    plan = {"routes": [], "tests": []}
    spec = {
        "journeys": [
            {
                "id": "j_changed",
                "title": "Changed Journey",
                "steps": [
                    {"do": "action", "section": "actions", "action": "rate"},
                    {"do": "expect", "section": "card-view", "changed": {"field": "dueDate"}, "live": True},
                ],
            }
        ]
    }
    code = journeys_spec(plan, spec, None)
    assert code is not None
    assert (
        'before_dueDate_0 = await readFieldValue(page.locator("[data-bga-section=\\"card-view\\"], '
        '[data-bga-section$=\\"/card-view\\"]"), "dueDate")' in code
    )
    assert "if (!process.env.LIVE_API)" in code
    assert 'test.skip(true, "live-only expectation")' in code
    assert "await expect.poll(async () =>" in code
    assert 'return await readFieldValue(sec, "dueDate")' in code
    assert "}).not.toBe(before_dueDate_0)" in code
