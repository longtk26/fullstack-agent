import json
import os
import shutil
from pathlib import Path

from src.engines.fake_engine import GOLDEN
from src.modules.shared.domain.backend_spec import validate_spec_text
from src.orchestrator.backend.planner import build_plan
from src.orchestrator.backend.scaffold import record_owned, scaffold_project

REPO = Path(__file__).parents[2]
EXAMPLES = REPO / "examples"
# Hand-written dynamic FrontendSpecs for the pair check's tests (tests/fixtures/pair-specs/README.md, Story 22.8)
PAIR_SPECS = Path(__file__).parent / "fixtures" / "pair-specs"
TEMPLATE = Path(os.environ["TEMPLATE_DIR"])
GOLDEN_PARTS = ("database", "projects", "tasks", "tests_projects", "tests_tasks")


def normalized(path: Path) -> dict:
    result = validate_spec_text(path.read_text())
    assert result.report.valid, result.report.errors
    return result.normalized


def two_entity_plan() -> dict:
    return build_plan(normalized(EXAMPLES / "specs" / "two-entity.json"))


def golden_project(root: Path) -> Path:
    """Template + overlay + the golden two-entity implementation (what the fake engine produces, repaired)."""
    project = root / "project"
    project.mkdir(parents=True)
    scaffold_project(TEMPLATE, project, "Project Tracker", plan=two_entity_plan())
    record_owned(project)
    for part in GOLDEN_PARTS:
        shutil.copytree(GOLDEN / part, project, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    (project / ".bga" / "plan.json").write_text(json.dumps(two_entity_plan()))
    return project


# The app outline the app flow drafts next to each example BackendSpec (Epic 22); `shop` has none (code fills it).
APP_OUTLINES = {
    "two-entity": "project-tracker",
    "flashcards": "flashcards",
    "workshop-bookings": "workshop-bookings",
    "shop": None,
}


def app_pair(backend_name: str, dashboard: bool = True) -> tuple[dict, dict]:
    """An app-flow FrontendSpec and its BackendSpec, as the app flow drafts them (Story 22.8: every dynamic
    FrontendSpec is an app): the example BackendSpec with the dashboard's operations added, and the pages code writes
    from the example outline. Both raw (valid) JSON documents. `dashboard=False`: an outline without a dashboard,
    so the BackendSpec stays the example's (tests that pin its contract, e.g. the golden two-entity OpenAPI)."""
    from src.modules.shared.domain.backend_spec import validate_spec_data
    from src.orchestrator.frontend.app.outline import complete_outline
    from src.orchestrator.frontend.app.screens import app_frontend_spec, ensure_aggregates
    from src.orchestrator.integration.contract import build_contract

    backend = validate_spec_data(json.loads((EXAMPLES / "specs" / f"{backend_name}.json").read_text())).normalized
    outline_name = APP_OUTLINES[backend_name]
    raw = json.loads((EXAMPLES / "app-outlines" / f"{outline_name}.json").read_text()) if outline_name else {}
    if not dashboard:
        raw = {key: value for key, value in raw.items() if key not in ("dashboard", "home")}
    outline, _ = complete_outline(raw, backend, build_contract(backend, build_plan(backend)))
    backend, outline, _ = ensure_aggregates(backend, outline)
    contract = build_contract(backend, build_plan(backend))
    screens = app_frontend_spec(backend, outline, {"colorScheme": "light-dark"}, contract)
    return screens.spec, backend


def write_app_pair(directory: Path, backend_name: str) -> tuple[Path, Path]:
    """`app_pair` written as `frontend-spec.json` / `backend-spec.json` into `directory`."""
    frontend, backend = app_pair(backend_name)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "frontend-spec.json").write_text(json.dumps(frontend, indent=2))
    (directory / "backend-spec.json").write_text(json.dumps(backend, indent=2))
    return directory / "frontend-spec.json", directory / "backend-spec.json"
