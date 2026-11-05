"""The fake engine's golden flashcards completion merges into the templated module (Story 22.4): an app flow
BackendSpec adds aggregate routes to `decks` and `cards`, and the golden custom-operation files must keep them, as an
engine's edit would (live: `deck.count` and `card.count` answered 404 when the golden router replaced the templated
one)."""

import json
import os
import re
from pathlib import Path

import pytest

from src.engines.fake_engine import GOLDEN_FLASHCARDS, GOLDEN_FLASHCARDS_BASE, merge_golden
from src.modules.shared.domain.backend_spec import validate_spec_data
from src.orchestrator.backend.codegen import module_files
from src.orchestrator.backend.planner import build_plan

EXAMPLES = Path(__file__).parents[2] / "examples"


def _templated(spec: dict, module: str) -> dict[str, str]:
    plan = build_plan(spec)
    return module_files(plan, spec, next(m for m in plan["modules"] if m["name"] == module))


@pytest.mark.parametrize("module", ["decks", "cards"])
def test_the_merge_base_is_the_templated_flashcards_module(module):
    """The base the golden files are merged against: the templates' output for `examples/specs/flashcards.json`, for
    each golden file the templates also write."""
    spec = validate_spec_data(json.loads((EXAMPLES / "specs" / "flashcards.json").read_text())).normalized
    files = _templated(spec, module)
    golden = GOLDEN_FLASHCARDS / module
    for source in sorted(golden.rglob("*.py")):
        relative = source.relative_to(golden).as_posix()
        if relative not in files:
            continue
        base = GOLDEN_FLASHCARDS_BASE / module / relative
        if os.environ.get("UPDATE_SNAPSHOTS") or not base.exists():
            base.parent.mkdir(parents=True, exist_ok=True)
            base.write_text(files[relative])
        assert base.read_text() == files[relative], f"{relative}: refresh with UPDATE_SNAPSHOTS=1"


def test_golden_custom_operations_merge_into_an_app_flow_module(tmp_path):
    import sys

    sys.path.insert(0, str(Path(__file__).parent))
    from test_app_screens import _example, _plan

    backend, raw = _example("flashcards")
    extended = _plan(backend, raw)[0]  # with the dashboard's aggregates (`deck.count`, `card.count`)
    for module in ("decks", "cards"):
        for relative, content in _templated(extended, module).items():
            (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / relative).write_text(content)
        merge_golden(GOLDEN_FLASHCARDS / module, GOLDEN_FLASHCARDS_BASE / module, tmp_path)
    decks = (tmp_path / "src/modules/decks/presenter/router.py").read_text()
    cards = (tmp_path / "src/modules/cards/presenter/router.py").read_text()
    assert {"deck.count", "deck.stats", "deck.list"} <= set(re.findall(r'operation_id="([^"]+)"', decks))
    assert {"card.count", "card.review", "card.listDue"} <= set(re.findall(r'operation_id="([^"]+)"', cards))
    exports = (tmp_path / "src/modules/decks/usecases/__init__.py").read_text()
    assert "CountDeckUsecaseDep" in exports and "StatsDeckUsecaseDep" in exports
    compile(decks, "router.py", "exec")


@pytest.mark.parametrize("module", ["decks", "cards"])
def test_the_per_module_completion_merges_too(tmp_path, module):
    """The backend lane completes each module in its own call; the fake picks the golden module by the prompt, and
    that step must merge as well (it once copied, so a live flashcards app lost `deck.count` again)."""
    from src.engines.fake_engine import FakeEngine, demo_scenario

    (tmp_path / ".bga").mkdir()
    (tmp_path / ".bga" / "spec.json").write_text(json.dumps({"project": {"name": "Flashcards"}}))
    engine = FakeEngine(tmp_path, demo_scenario(delay_s=0))
    step = engine._next_step(tmp_path, "complete_backend", f"... complete the `{module}` module ...")
    assert step.copy_from == GOLDEN_FLASHCARDS / module and step.merge_base == GOLDEN_FLASHCARDS_BASE / module
