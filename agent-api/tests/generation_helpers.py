import json
import os
import shutil
from pathlib import Path

from src.engines.fake_engine import GOLDEN
from src.modules.shared.domain.backend_spec import validate_spec_text
from src.orchestrator.planner import build_plan
from src.orchestrator.scaffold import record_owned, scaffold_project

REPO = Path(__file__).parents[2]
EXAMPLES = REPO / "examples"
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
    scaffold_project(TEMPLATE, project, "Project Tracker")
    record_owned(project)
    for part in GOLDEN_PARTS:
        shutil.copytree(GOLDEN / part, project, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    (project / ".bga" / "plan.json").write_text(json.dumps(two_entity_plan()))
    return project


def engine_path(frontend_spec: dict) -> dict:
    """A copy of a FrontendSpec whose custom components have no props schema, so its frontend lane takes the engine
    path (for the shop: the golden `corner_shop` frontend) instead of the renderer and custom components (17.3)."""
    spec = json.loads(json.dumps(frontend_spec))
    for component in spec.get("components", []):
        component.pop("propsSchema", None)
    return spec
