"""Static golden (Story 22.1): static sites draft and render byte for byte as before.

Epic 22 gives dynamic apps their own frontend flow; static mode must not change. For each static example and one
static requirement, on the fake engine: draft (designed pages on, as in production), normalize, plan and scaffold the
frontend, then compare a digest of every output file (the FrontendSpec, the plan, `site.json`, page files, CSS, the
library files) with `tests/fixtures/static-golden/`. `UPDATE_SNAPSHOTS=1` rewrites them; a story that does must say
so in its Status.
"""

import asyncio
import hashlib
import json
import os
import uuid
from pathlib import Path

import pytest
from sqlmodel import Session, delete

from src.configs import config
from src.engines import EngineRegistry, PromptLibrary
from src.engines.fake_engine import FakeEngine, FakeStep, demo_scenario
from src.libs.database import db_session_manager
from src.modules.shared.domain.frontend_spec import validate_frontend_spec_data
from src.modules.shared.infrastructure.models import SpecDraftModel
from src.orchestrator.drafting.drafts import DraftRunner
from src.orchestrator.frontend.planner import dump_frontend_plan, plan_frontend
from src.orchestrator.frontend.scaffold import scaffold_frontend
from src.orchestrator.store import JobStore

REPO = Path(__file__).parents[2]
EXAMPLES = REPO / "examples"
GOLDEN = Path(__file__).parent / "fixtures" / "static-golden"
SEED = 7
# Base files are pinned by `overlay.json` (the scaffold fails on drift), so only what the generator writes counts.
SKIP_PREFIXES = ("node_modules/",)

pytestmark = pytest.mark.usefixtures("clean_redis")


@pytest.fixture(autouse=True)
def golden_settings(monkeypatch):
    monkeypatch.setattr(config, "frontend_trees", True)  # production drafts design pages
    monkeypatch.setattr(config, "image_provider", "none")  # placeholders become drawings, not uploads with new ids
    yield
    with Session(db_session_manager.engine) as session:
        session.exec(delete(SpecDraftModel))
        session.commit()


def _example_engine(root: Path, example: str) -> FakeEngine:
    """A fake engine that drafts the example as it is (no direction cards: the code-picked directions apply)."""
    spec = (EXAMPLES / "frontend-specs" / example).read_text()
    notes = {"assumptions": [{"spec": "frontend", "path": "", "message": f"Fake engine: {example}"}], "unresolved": []}
    return FakeEngine(
        root,
        {
            "draft_frontend_spec": [FakeStep(write={"frontend-spec.json": spec, "notes.json": json.dumps(notes)})],
            "draft_tree": [FakeStep(tree_fixture=True)],
        },
    )


CASES = {
    "static-landing": (lambda root: _example_engine(root, "static-landing.json"), "A studio site. " * 4),
    "street-food-static": (lambda root: _example_engine(root, "street-food-static.json"), "A street food stall. " * 3),
    "northwind-requirement": (
        lambda root: FakeEngine(root, demo_scenario(delay_s=0)),
        (EXAMPLES / "requirements" / "northwind-studio.md").read_text(),
    ),
}


def _draft(client, headers, root: Path, engine: FakeEngine, text: str) -> dict:
    body = {"engine": "fake", "mode": "static", "requirementText": text, "designSeed": SEED}
    response = client.post("/api/v1/spec-drafts", json=body, headers=headers)
    assert response.status_code == 202, response.text
    draft_id = response.json()["draftId"]
    runner = DraftRunner(EngineRegistry([engine], default="fake"), PromptLibrary(), JobStore(), root, "w-golden")
    asyncio.run(runner.run(draft_id))
    draft = JobStore().draft(uuid.UUID(draft_id)).model_dump(mode="json")
    assert draft["status"] == "SUCCEEDED", draft["validation"]
    return draft


def _digest(text: bytes) -> str:
    return hashlib.sha256(text).hexdigest()


def render_digests(spec: dict, project: Path) -> dict[str, str]:
    """Digests of the normalized spec, the plan and every file the scaffold writes that is not pinned base code."""
    normalized = validate_frontend_spec_data(spec).normalized
    assert normalized is not None
    plan = plan_frontend(normalized)
    scaffold_frontend(project, plan, normalized)
    digests = {
        "(frontend-spec)": _digest(json.dumps(spec, sort_keys=True, ensure_ascii=False).encode()),
        "(plan)": _digest(dump_frontend_plan(plan).encode()),
    }
    for path in sorted(project.rglob("*")):
        relative = path.relative_to(project).as_posix()
        if path.is_file() and not relative.startswith(SKIP_PREFIXES):
            digests[relative] = _digest(path.read_bytes())
    return digests


@pytest.mark.parametrize("case", sorted(CASES))
def test_static_sites_draft_and_render_as_before(case, client, user_headers, tmp_path):
    make_engine, text = CASES[case]
    draft = _draft(client, user_headers, tmp_path, make_engine(tmp_path), text)
    assert draft["frontend_spec"]["project"]["mode"] == "static"
    digests = render_digests(draft["frontend_spec"], tmp_path / "site")
    golden = GOLDEN / f"{case}.json"
    text_out = json.dumps(digests, indent=2, sort_keys=True) + "\n"
    if os.environ.get("UPDATE_SNAPSHOTS") or not golden.exists():
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text(text_out)
    recorded = json.loads(golden.read_text())
    changed = sorted(k for k in recorded.keys() & digests.keys() if recorded[k] != digests[k])
    added, removed = sorted(digests.keys() - recorded.keys()), sorted(recorded.keys() - digests.keys())
    assert not (changed or added or removed), (
        f"static output changed (Story 22.1): changed {changed}, added {added}, removed {removed}; static mode must "
        "not change in Epic 22 (rerun with UPDATE_SNAPSHOTS=1 only with a note in the story)"
    )
