"""Epic 21 (Story 21.6): drafts design their pages as trees; the fake engine composes them from the sections."""

import copy
import json
from pathlib import Path

from generation_helpers import EXAMPLES
from test_drafting import REQUIREMENTS, _create, _run

from src.configs import config
from src.engines import PromptLibrary
from src.engines.fake_trees import fake_tree
from src.modules.shared.domain.frontend_spec import validate_frontend_spec_data
from src.orchestrator.drafting.trees import apply_tree_files, complete_backend_for_trees, prompt_context, tree_requests
from src.orchestrator.frontend.planner import plan_frontend

LANDING = json.loads((EXAMPLES / "frontend-specs" / "static-landing.json").read_text())
TRACKER = json.loads((EXAMPLES / "frontend-specs" / "project-tracker-dynamic.json").read_text())


def test_the_tree_prompt_carries_the_outline_the_direction_and_the_rules():
    spec = validate_frontend_spec_data(LANDING).normalized
    requests = tree_requests(spec)
    assert [r["id"] for r in requests][-1] == "chrome" and requests[0]["output_path"] == "trees/home.json"
    assert requests[0]["sections"][0]["component"] == "Hero" and "content" in requests[0]["sections"][0]
    context = prompt_context(spec, requests[0], inline=True)
    text = PromptLibrary().render("draft_tree", "v1", **context).text
    assert '"files": {"trees/home.json"' in text and "## The direction" in text and "CollectionBrowser" in text
    assert "One `h1` on a page" in text and f"At most {context['max_nodes']} nodes" in text
    assert "Pages, for `Link`" in text and "`home`" in text
    path_text = PromptLibrary().render("draft_tree", "v1", **{**context, "inline": False}).text
    assert "Write `trees/home.json` as JSON" in path_text and '"files"' not in path_text
    chrome = PromptLibrary().render("draft_tree", "v1", **prompt_context(spec, requests[-1], inline=True)).text
    assert "This is the site chrome" in chrome


def test_the_fake_composes_a_designed_page_from_the_sections():
    spec = validate_frontend_spec_data(LANDING).normalized
    home = spec["pages"][0]
    tree = fake_tree(home, spec, seed=1)
    types = [child["type"] for child in tree["children"]]
    assert tree["type"] == "main" and types[0] == "section", "the hero becomes a designed section"
    hero = tree["children"][0]
    assert hero["children"][0]["children"][1]["type"] == "h1" or hero["children"][0]["children"][0]["type"] == "h1"
    assert any(child["type"] in ("Features", "section") for child in tree["children"][1:])
    flipped = fake_tree(home, spec, seed=2)
    assert flipped != tree, "the seed varies the composition"


def test_a_static_draft_designs_every_page(client, user_headers, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "frontend_trees", True)
    draft_id = _create(client, user_headers, "static", (REQUIREMENTS / "northwind-studio.md").read_text(), designSeed=3)
    draft = _run(tmp_path, draft_id)
    assert draft["status"] == "SUCCEEDED", draft["validation"]
    prompts = [call["prompt"] for call in draft["usage"]["calls"]]
    pages = draft["frontend_spec"]["pages"]
    assert prompts[0] == "draft_frontend_spec@v10" and prompts.count("draft_tree@v1") == len(pages) + 1, prompts
    assert all(page.get("tree") for page in pages), [page["route"] for page in pages if not page.get("tree")]
    assert pages[0]["css"].startswith('[data-page="home"] .fake-rug'), "the page CSS is scoped by the draft"
    assert pages[0]["tree"]["children"][0]["props"]["animate"]["type"] == "fade-up"
    assert not any("dropped" in note["message"] for note in draft["assumptions"]), draft["assumptions"]
    plan = plan_frontend(validate_frontend_spec_data(draft["frontend_spec"]).normalized)
    assert plan["trees"] is True and plan["rendering"] == "renderer"


def test_a_dynamic_draft_designs_its_pages_and_binds_them_to_the_contract(client, user_headers, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "frontend_trees", True)
    draft_id = _create(client, user_headers, "dynamic", (REQUIREMENTS / "project-tracker.md").read_text(), designSeed=5)
    draft = _run(tmp_path, draft_id)
    assert draft["status"] == "SUCCEEDED", draft["validation"]
    pages = draft["frontend_spec"]["pages"]
    assert all(page.get("tree") for page in pages)
    from src.modules.shared.domain.backend_spec import validate_spec_data
    from src.orchestrator.integration.contract import build_contract

    contract = build_contract(validate_spec_data(draft["backend_spec"]).normalized)
    plan = plan_frontend(validate_frontend_spec_data(draft["frontend_spec"]).normalized, contract)
    assert plan["rendering"] == "renderer" and plan["trees"] is True
    from src.orchestrator.frontend.renderer import site_data

    site = site_data(plan, validate_frontend_spec_data(draft["frontend_spec"]).normalized, contract)
    bound = [
        node
        for page in site["pages"].values()
        for node in _walk(page["tree"])
        if node.get("kind") == "data" and node.get("binding")
    ]
    assert bound and all(b["binding"].get("operationId") for b in bound), "every data component binds to an operation"


def _walk(node):
    if isinstance(node, dict):
        yield node
        for child in node.get("children") or []:
            yield from _walk(child)


def test_a_tree_that_breaks_the_rules_costs_only_its_page(tmp_path):
    work = tmp_path
    spec = copy.deepcopy(LANDING)
    (work / "frontend-spec.json").write_text(json.dumps(spec))
    (work / "trees").mkdir()
    good = {"tree": {"type": "main", "children": [{"type": "h1", "children": ["Hi"]}]}, "css": ".x { color: red }"}
    bad = {"tree": {"type": "main", "children": [{"type": "img", "props": {"src": "asset:nope", "alt": ""}}]}}
    (work / "trees" / "home.json").write_text(json.dumps(good))
    (work / "trees" / "about.json").write_text(json.dumps(bad))
    (work / "trees" / "work.json").write_text("{not json")
    notes = apply_tree_files(work, work / "frontend-spec.json")
    result = json.loads((work / "frontend-spec.json").read_text())
    pages = {p["id"] if p.get("id") else p["route"]: p for p in result["pages"]}
    home = next(p for p in result["pages"] if p["route"] == "/")
    assert home["tree"]["children"][0]["type"] == "h1" and home["css"].startswith('[data-page="home"] .x')
    messages = " | ".join(note["message"] for note in notes)
    assert "Page 'work': tree is not JSON" in messages or "is not JSON" in messages
    dropped = [p for p in result["pages"] if "tree" not in p]
    assert len(dropped) >= 2 and all(p.get("sections") for p in dropped), "pages without a valid tree keep sections"
    assert validate_frontend_spec_data(result).report.valid
    assert pages is not None


def test_dynamic_trees_add_the_operations_and_entities_they_need(tmp_path):
    spec = {
        "specVersion": "1.0",
        "project": {"name": "Money", "mode": "dynamic"},
        "pages": [
            {
                "route": "/",
                "title": "Dashboard",
                "tree": {
                    "type": "main",
                    "children": [
                        {
                            "type": "Metric",
                            "props": {"collection": "expenses", "fn": "sum", "field": "amount", "period": "month"},
                        },
                        {
                            "type": "Chart",
                            "props": {"collection": "expenses", "kind": "bar", "fn": "count", "groupBy": "category"},
                        },
                        {
                            "type": "CollectionBrowser",
                            "props": {"collection": "expenses", "sortFields": ["spentAt"]},
                            "children": [],
                        },
                    ],
                },
            }
        ],
        "content": [
            {
                "collection": "expenses",
                "records": [
                    {"id": "e1", "title": "Coffee", "amount": 3.5, "category": "Food", "spentAt": "2026-11-01"},
                    {"id": "e2", "title": "Bus", "amount": 2.0, "category": "Travel", "spentAt": "2026-11-02"},
                ],
            }
        ],
    }
    backend = {
        "specVersion": "1.0",
        "project": {"name": "Money"},
        "stack": {"framework": "fastapi", "database": "postgresql", "orm": "sqlmodel", "migration": "alembic"},
        "entities": [
            {
                "name": "Category",
                "fields": [{"name": "id", "type": "uuid", "primary": True}, {"name": "name", "type": "string"}],
            }
        ],
        "operations": [
            {
                "operationId": "category.list",
                "type": "crud",
                "action": "list",
                "entity": "Category",
                "method": "GET",
                "path": "/categories",
            }
        ],
    }
    (tmp_path / "frontend-spec.json").write_text(json.dumps(spec))
    (tmp_path / "backend-spec.json").write_text(json.dumps(backend))
    notes = complete_backend_for_trees(tmp_path / "frontend-spec.json", tmp_path / "backend-spec.json")
    result = json.loads((tmp_path / "backend-spec.json").read_text())
    expense = next(e for e in result["entities"] if e["name"] == "Expense")
    assert {f["name"]: f["type"] for f in expense["fields"]} == {
        "id": "string",
        "title": "string",
        "amount": "float",
        "category": "string",
        "spentAt": "date",
    }
    ids = [op["operationId"] for op in result["operations"]]
    assert ids == ["category.list", "expense.sumAmount", "expense.countByCategory", "expense.list", "expense.get"]
    assert next(op for op in result["operations"] if op["operationId"] == "expense.sumAmount")["aggregate"] == {
        "fn": "sum",
        "field": "amount",
        "period": "month",
    }
    assert result["seed"][0]["entity"] == "Expense" and len(result["seed"][0]["records"]) == 2
    assert any("Entity 'Expense' added" in n["message"] for n in notes) and any(
        "Operations added" in n["message"] for n in notes
    )
    from src.modules.shared.domain.backend_spec import validate_spec_data

    assert validate_spec_data(result).report.valid, validate_spec_data(result).report.errors
    assert Path(tmp_path / "backend-spec.json").is_file()
