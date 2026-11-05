"""The dynamic app flow's switch (Story 22.1): `DYNAMIC_FRONTEND=app` sends dynamic drafts to their own flow, the
frontend lane plans and scaffolds them on the app kit, and nothing of it reaches static sites or legacy drafts."""

import asyncio
import json
import uuid
from pathlib import Path

import pytest
from sqlmodel import Session, delete

from src.configs import config
from src.engines import EngineRegistry, PromptLibrary
from src.engines.fake_engine import FakeEngine, demo_scenario
from src.libs.database import db_session_manager
from src.modules.shared.domain.backend_spec import validate_spec_data
from src.modules.shared.domain.frontend_spec import frontend_spec_json_schema, validate_frontend_spec_data
from src.modules.shared.infrastructure.models import SpecDraftModel
from src.orchestrator.backend.planner import build_plan
from src.orchestrator.drafting.drafts import DraftRunner
from src.orchestrator.frontend.app.screens import app_frontend_spec
from src.orchestrator.frontend.planner import plan_frontend
from src.orchestrator.frontend.scaffold import scaffold_frontend
from src.orchestrator.integration.contract import build_contract
from src.orchestrator.store import JobStore

REPO = Path(__file__).parents[2]
EXAMPLES = REPO / "examples"

pytestmark = pytest.mark.usefixtures("clean_redis")


@pytest.fixture
def cleanup_drafts():
    yield
    with Session(db_session_manager.engine) as session:
        session.exec(delete(SpecDraftModel))
        session.commit()


def _backend(name: str) -> dict:
    return validate_spec_data(json.loads((EXAMPLES / "specs" / f"{name}.json").read_text())).normalized


def _draft(client, headers, root: Path, mode: str, text: str) -> dict:
    response = client.post(
        "/api/v1/spec-drafts", json={"engine": "fake", "mode": mode, "requirementText": text}, headers=headers
    )
    assert response.status_code == 202, response.text
    draft_id = response.json()["draftId"]
    engine = FakeEngine(root, demo_scenario(delay_s=0))
    runner = DraftRunner(EngineRegistry([engine], default="fake"), PromptLibrary(), JobStore(), root, "w-app", EXAMPLES)
    asyncio.run(runner.run(draft_id))
    return JobStore().draft(uuid.UUID(draft_id)).model_dump(mode="json")


def test_app_flow_drafts_reach_the_new_path(client, user_headers, tmp_path, monkeypatch, cleanup_drafts):
    monkeypatch.setattr(config, "dynamic_frontend", "app")
    monkeypatch.setattr(config, "frontend_trees", True)  # the app flow designs no pages, whatever this says
    draft = _draft(
        client, user_headers, tmp_path, "dynamic", (EXAMPLES / "requirements" / "project-tracker.md").read_text()
    )
    assert draft["status"] == "SUCCEEDED", draft["validation"]
    spec = draft["frontend_spec"]
    assert spec["project"] == {"name": spec["app"]["name"], "mode": "dynamic", "flow": "app"} | (
        {"description": spec["project"]["description"]} if "description" in spec["project"] else {}
    )
    assert [call["prompt"].split("@")[0] for call in draft["usage"]["calls"]] == ["draft_app"], "no trees, no cards"
    assert draft["design"] is None and set(draft["validation"]) == {"backend", "frontend", "pair"}
    assert draft["validation"]["pair"]["valid"] is True
    assert any(note["message"].startswith("Design direction: ") for note in draft["assumptions"])
    assert spec["theme"]["colorScheme"] == "light-dark" and "motion" not in spec["theme"]


def test_static_and_legacy_drafts_stay_on_their_flow(client, user_headers, tmp_path, cleanup_drafts):
    assert config.dynamic_frontend == "legacy", "the default until Story 22.4 is accepted"
    draft = _draft(
        client, user_headers, tmp_path, "dynamic", (EXAMPLES / "requirements" / "project-tracker.md").read_text()
    )
    assert "flow" not in draft["frontend_spec"]["project"] and "app" not in draft["frontend_spec"]
    assert draft["usage"]["calls"][0]["prompt"] == "draft_frontend_spec@v10"


def test_an_empty_outline_renders_a_shell_with_no_screens(tmp_path):
    backend = _backend("two-entity")
    spec = app_frontend_spec(backend, {}, {"colorScheme": "light-dark"}).spec  # no contract: the bare shell
    result = validate_frontend_spec_data(spec)
    assert result.report.valid, result.report.errors
    contract = build_contract(backend, build_plan(backend))
    plan = plan_frontend(result.normalized, contract)
    assert plan["rendering"] == "app" and plan["rendererGaps"] == [] and plan["trees"] is False
    assert [route["route"] for route in plan["routes"]] == ["/"]
    assert plan["shell"]["file"] == "src/components/layout/SiteShell.tsx" and "sidebar" in plan["shadcn"]
    scaffold_frontend(tmp_path, plan, result.normalized, contract)
    app = json.loads((tmp_path / "src/content/app.json").read_text())
    assert app["nav"] == [] and list(app["pages"]) == ["home"]
    assert "AppShell" in (tmp_path / "src/components/layout/SiteShell.tsx").read_text()
    assert (tmp_path / "src/components/app/AppPage.tsx").is_file() and (
        tmp_path / "src/components/app/bindings.ts"
    ).is_file()
    assert 'AppPage pageId="home"' in (tmp_path / "src/app/page.tsx").read_text()
    assert not (tmp_path / "app").exists(), "the kit lands at its project paths"
    assert not (tmp_path / "src/components/renderer").exists() and not (tmp_path / "src/components/sections").exists()


def test_legacy_dynamic_scaffolds_without_the_kit(tmp_path):
    backend = _backend("two-entity")
    spec = validate_frontend_spec_data(
        json.loads((EXAMPLES / "frontend-specs/project-tracker-dynamic.json").read_text())
    )
    contract = build_contract(backend, build_plan(backend))
    plan = plan_frontend(spec.normalized, contract)
    scaffold_frontend(tmp_path, plan, spec.normalized, contract)
    assert plan["rendering"] == "renderer" and not (tmp_path / "src/components/app").exists()


def _spec(**changes) -> dict:
    spec = {
        "specVersion": "1.0",
        "project": {"name": "Tracker", "mode": "dynamic", "flow": "app"},
        "app": {"name": "Tracker"},
        "pages": [{"route": "/", "title": "Home", "sections": [{"id": "dash", "component": "AppDashboard"}]}],
    }
    for key, value in changes.items():
        spec[key] = value
    return spec


def test_app_sections_and_the_outline_belong_to_the_app_flow():
    assert validate_frontend_spec_data(_spec()).report.valid
    static = validate_frontend_spec_data(_spec(project={"name": "Site", "mode": "static", "flow": "app"})).report
    assert "FE_APP_FLOW" in {issue.code for issue in static.errors}
    legacy = validate_frontend_spec_data(_spec(project={"name": "Tracker", "mode": "dynamic"})).report
    codes = {issue.code: issue.path for issue in legacy.errors}
    assert codes["FE_APP_FLOW"] == "/app" and codes["FE_UNKNOWN_COMPONENT"] == "/pages/0/sections/0/component"


def test_static_and_legacy_drafts_read_the_schema_without_the_app_flow():
    full, site = frontend_spec_json_schema(), frontend_spec_json_schema(app=False)
    assert "app" in full["properties"] and "flow" in full["$defs"]["Project"]["properties"]
    assert "app" not in site["properties"] and "flow" not in site["$defs"]["Project"]["properties"]
    assert not any(name.startswith("App") for name in site["$defs"])
