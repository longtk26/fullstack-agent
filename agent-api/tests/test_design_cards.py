"""Stories 20.4 and 20.9: direction cards checked and filled, the difference test and its fixes, home pages composed
from the drafted pool, the fake engine's concept library, and the UI's mirror of `apply_direction`."""

import asyncio
import copy
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from src.engines.fake_design import concepts, fake_cards
from src.modules.shared.domain.frontend_spec import FONTS, validate_frontend_spec_data
from src.modules.shared.domain.frontend_spec.copy_rules import stock_phrase
from src.orchestrator.design_cards import (
    HERO_LAYOUTS,
    Card,
    best_fit,
    brand_fixed,
    card_directions,
    code_fix,
    compose,
    fact_pack,
    fill_card,
    home_pool,
    problems,
    read_cards,
)
from src.orchestrator.design_direction import apply_direction, contrast_failures, directions
from src.orchestrator.design_diversity import hue_family
from src.orchestrator.drafting import FRONTEND_FILE, NOTES_FILE, settle_directions
from tests.generation_helpers import EXAMPLES

REPO = Path(__file__).parents[2]
LANDING = json.loads((EXAMPLES / "frontend-specs" / "static-landing.json").read_text())
TRACKER = json.loads((EXAMPLES / "frontend-specs" / "project-tracker-dynamic.json").read_text())
SPA = "A day spa in Leeds offering massages, facials and wellness treatments. Clients book a treatment."
FLOORS = directions(SPA)
POOL = home_pool(LANDING)
DEFAULT = FLOORS[0]["homeOrder"]


def card(**overrides) -> Card:
    data = {
        "name": "Steam and cedar",
        "concept": "The quiet of a cedar sauna.",
        "engine": "material",
        "tone": {"energy": 1, "finish": 4, "density": 2, "weight": 2, "seriousness": 3},
        "heroLayout": "centered",
        "fonts": {"heading": "Cormorant Garamond", "body": "Source Sans 3"},
        "colors": {"primary": "#7c4a2d", "background": "#f6f1ea", "source": "cedar wood"},
        "keyVisual": "type",
        "givesUp": "Big photos",
        "fit": 1,
    }
    return Card.model_validate(data | overrides)


def filled(**overrides) -> dict:
    return fill_card(card(**overrides), FLOORS[0], POOL, [], 7)[0]


# -- cards -----------------------------------------------------------------------------------------------------------


def test_cards_are_read_leniently_in_the_engines_order():
    cards, notes = read_cards({"cards": [{"name": "A", "fit": 2}, "not a card", {"name": "B", "fit": 1}, {}, {}]})
    assert [c.name for c in cards] == ["A", "B", ""] and len(notes) == 1, "the engine's order: numbers stay"
    assert read_cards({"productType": "SaaS"}) == ([], [])


def test_a_card_keeps_its_good_fields_when_one_cannot_be_read():
    motion = {"name": "A", "motion": {"feel": "flow", "signature": "headlineRise"}, "concept": "x" * 400}
    cards, notes = read_cards({"cards": [motion, {"name": "B", "home": "hero", "rhythm": "alternate"}]})
    assert (cards[0].motion, cards[0].signature, len(cards[0].concept)) == ("flow", "headlineRise", 300)
    assert cards[1].name == "B" and cards[1].home is None and cards[1].rhythm == "alternate"
    assert notes == ["Card 2: home could not be read; the default is used"]


def test_a_card_is_filled_into_a_theme_with_tone_tokens_and_its_record():
    direction = filled()
    theme = direction["theme"]
    assert theme["typography"]["headingFont"] == "Cormorant Garamond" and theme["colors"]["primary"] == "#7c4a2d"
    assert theme["colorArea"] == "minimal" and theme["surface"] == "raised" or theme["surface"] == "flat"
    assert theme["typography"]["headingWeight"] == 500 and theme["style"] == "editorial"
    assert theme["direction"] | {} == theme["direction"] and theme["direction"]["name"] == "Steam and cedar"
    assert theme["direction"]["seed"] == 7 and theme["direction"]["tone"]["energy"] == 1
    assert direction["home"] == ["hero", "services", "quotes", "cta"] and direction["source"] == "card"
    assert not contrast_failures(theme)
    spec = apply_direction(LANDING, direction, POOL)
    assert validate_frontend_spec_data(spec).report.valid, "the filled theme is a valid FrontendSpec theme"


def test_unknown_values_are_fixed_with_notes():
    direction, notes = fill_card(
        card(heroLayout="diagonal", fonts={"heading": "Playfair", "body": "Space Mono"}, keyVisual="hologram"),
        FLOORS[0],
        POOL,
        [],
        1,
    )
    assert direction["heroVariant"] == "split" and direction["keyVisual"] == "photo"
    assert direction["theme"]["typography"] == direction["theme"]["typography"] | {
        "headingFont": "Playfair Display",
        "bodyFont": "Inter",
    }
    assert any("hero layout" in note for note in notes) and any("fonts" in note for note in notes)


def test_layouts_follow_the_hero_and_the_key_visual():
    assert filled(heroLayout="collage", keyVisual="photo")["heroVariant"] == "stacked", "the hero has one image"
    assert filled(heroLayout="split", keyVisual="type")["heroVariant"] == "type"
    assert filled(heroLayout="type", keyVisual="photo")["keyVisual"] == "type"


def test_colours_that_miss_contrast_are_fixed_or_floored():
    fixed = filled(colors={"primary": "#ffd84d", "background": "#ffffff", "foreground": "#bbbbbb", "source": "lemon"})
    assert not contrast_failures(fixed["theme"]) and fixed["theme"]["colors"]["foreground"] == "#0a0a0a"
    assert hue_family(fixed["theme"]["colors"]["primary"]) == "h30"
    assert fixed["notes"] == ["foreground #bbbbbb → #0a0a0a for AA contrast"]
    dark_surface = filled(colors={"primary": "#7c4a2d", "background": "#ffffff", "muted": "#111111", "source": "?"})
    assert dark_surface["theme"]["colors"] == FLOORS[0]["theme"]["colors"]
    assert "missed AA contrast" in dark_surface["palette"]
    unreadable = filled(colors={"primary": "not a colour", "background": "#fff", "source": "?"})
    assert unreadable["theme"]["colors"] == FLOORS[0]["theme"]["colors"] and "did not parse" in unreadable["palette"]


def test_the_best_fit_is_selected():
    directions_ = [filled(fit=2), filled(fit=1), filled(fit=3)]
    assert best_fit(directions_) == 1


# -- the difference test ---------------------------------------------------------------------------------------------


def test_three_alike_cards_fail_and_code_makes_them_differ():
    same = [card(heroLayout="split", keyVisual="photo", fit=i) for i in (1, 2, 3)]
    kept, _ = card_directions(same, FLOORS, POOL, [], 3, None)
    found = problems(kept, DEFAULT, POOL, set())
    assert any("share" in p for p in found) and any("same hero layout" in p for p in found)
    assert any("open" in p for p in found)
    notes = code_fix(kept, DEFAULT, POOL, [], set())
    assert problems(kept, DEFAULT, POOL, set()) == [] and notes
    assert len({d["heroVariant"] for d in kept}) == 3 and len({d["home"][1] for d in kept} | {kept[2]["home"][2]}) > 1
    for direction in kept:
        assert not contrast_failures(direction["theme"]) and direction["heroVariant"] in HERO_LAYOUTS
        assert direction["theme"]["direction"]["fontPairing"] == direction["fontPairing"]


def test_brand_colours_and_fonts_are_not_counted_as_shared():
    brand = {"colors": {"primary": "#0e7490"}, "fonts": {"headingFont": "Lora"}}
    assert brand_fixed(brand) == {"hueFamily", "headingFont"}
    cards = [card(heroLayout=layout, keyVisual=kv, fit=i) for i, (layout, kv) in enumerate(
        [("split", "photo"), ("type", "type"), ("stage", "illustration")]
    )]  # fmt: skip
    kept, _ = card_directions(cards, FLOORS, POOL, [], 3, brand)
    assert all(d["theme"]["colors"]["primary"] == "#0e7490" for d in kept)
    assert not [p for p in problems(kept, DEFAULT, POOL, brand_fixed(brand)) if "share" in p]


def test_an_app_home_without_a_hero_compares_font_and_hue_only():
    pool = home_pool(TRACKER)
    cards = [
        card(heroLayout="split", keyVisual="photo", fonts={"heading": f, "body": "Inter"}, home=["stats", "recent"])
        for f in ("Inter", "Lora", "Syne")
    ]
    kept, _ = card_directions(cards, FLOORS, pool, [], 3, None)
    assert not [p for p in problems(kept, [], pool, set()) if "share" in p], "same layout and visual do not count"


# -- home pages from the pool (20.9) ---------------------------------------------------------------------------------


def test_a_home_page_keeps_the_hero_first_and_the_required_sections():
    assert compose(["quotes", "services"], POOL, []) == ["hero", "quotes", "services"]
    assert compose(["services", "unknown"], POOL, ["cta"]) == ["hero", "services", "cta"]
    assert compose(["services"], POOL, ["quotes"]) == ["hero", "services", "quotes"]
    assert compose(None, POOL, []) == ["hero", "services", "quotes", "cta"]


def test_switching_directions_restores_left_out_sections_and_keeps_edits():
    short = filled(home=["hero", "services", "cta"])
    full = filled(home=["hero", "quotes", "services", "cta"])
    applied = apply_direction(LANDING, short, POOL)
    home = next(p for p in applied["pages"] if p["route"] == "/")
    assert [s["id"] for s in home["sections"]] == ["hero", "services", "cta"]
    home["sections"][1]["content"] = {"title": "Edited by the user"}
    home["sections"].insert(2, {"id": "mine", "component": "RichText", "content": {"body": "added"}})
    back = apply_direction(applied, full, POOL)
    home = next(p for p in back["pages"] if p["route"] == "/")
    assert [s["id"] for s in home["sections"]] == ["hero", "quotes", "services", "mine", "cta"]
    assert home["sections"][2]["content"]["title"] == "Edited by the user"


def test_a_card_sets_forms_and_rhythm_everywhere_and_a_later_one_resets_them():
    ledger = filled(sectionForms={"Features": "ledger", "Testimonials": "quote"}, rhythm="alternate")
    applied = apply_direction(LANDING, ledger, POOL)
    features = [s for p in applied["pages"] for s in p["sections"] if s["component"] == "Features"]
    assert {s["content"]["form"] for s in features} == {"ledger"} and len(features) == 2
    assert {p.get("rhythm") for p in applied["pages"]} == {"alternate"}
    alternating = filled(sectionForms={"Features": "alternating"})
    again = apply_direction(applied, alternating, POOL)
    features = [s for p in again["pages"] for s in p["sections"] if s["component"] == "Features"]
    assert {s["content"]["form"] for s in features} == {"list"}, "no item images: list"
    assert not any("rhythm" in p for p in again["pages"])
    testimonials = [s for p in again["pages"] for s in p["sections"] if s["component"] == "Testimonials"]
    assert "form" not in testimonials[0]["content"]


# -- the fake engine's library ---------------------------------------------------------------------------------------


def test_the_concept_library_is_usable():
    library = concepts()
    assert len(library) >= 40 and len({c["name"] for c in library}) == len(library)
    for concept in library:
        assert concept["heroLayout"] in HERO_LAYOUTS and concept["fonts"]["heading"] in FONTS
        assert concept["fonts"]["body"] in FONTS
        direction = fill_card(Card.model_validate(concept), FLOORS[0], POOL, [], 1)[0]
        notes = [note for note in direction["notes"] if "collage hero" not in note]  # the example hero has one image
        assert not notes, (concept["name"], notes)


def test_fake_cards_are_seeded_varied_and_pass_the_difference_test():
    first, again, other = (fake_cards(SPA, seed, POOL) for seed in (11, 11, 12))
    assert first == again and first != other
    for cards in (first, other):
        kept, _ = card_directions([Card.model_validate(c) for c in cards], FLOORS, POOL, [], 1, None)
        assert problems(kept, DEFAULT, POOL, set()) == []
    matching = {c["name"] for c in concepts() if any(word in SPA.lower() for word in c["keywords"])}
    picked = [c["name"] for seed in range(40) for c in fake_cards(SPA, seed, POOL)]
    share, base = sum(name in matching for name in picked) / len(picked), len(matching) / len(concepts())
    assert share > 2 * base, "the brief matters"
    assert all(len({c["heroLayout"] for c in fake_cards(SPA, seed, POOL)}) == 3 for seed in range(40))


# -- drafting: repairs and the code fallback -------------------------------------------------------------------------


def _work(tmp_path: Path, cards: list[dict], **design) -> Path:
    (tmp_path / FRONTEND_FILE).write_text(json.dumps(LANDING))
    (tmp_path / NOTES_FILE).write_text(json.dumps({"design": {"cards": cards, **design}}))
    return tmp_path


def test_a_failing_card_is_asked_again_then_fixed_by_code(tmp_path):
    alike = [card(heroLayout="split", keyVisual="photo", fit=i).model_dump(by_alias=True) for i in (1, 2, 3)]
    work = _work(tmp_path, alike)
    asked = []

    async def repair(index, found, kept):
        asked.append(index)
        notes = json.loads((work / NOTES_FILE).read_text())
        if len(asked) == 1:  # the first round rewrites the card; the second changes nothing
            notes["design"]["cards"][index] = concepts()[0] | {"fit": 2}
        (work / NOTES_FILE).write_text(json.dumps(notes))

    design = asyncio.run(settle_directions(work, FLOORS, 5, repair))
    assert asked[0] == 1 and len(asked) == 2
    assert problems(design["directions"], DEFAULT, POOL, set()) == []
    assert design["notes"][0] == "Directions asked again 2 time(s) to differ from each other"
    assert design["seed"] == 5 and design["selected"] == 0


def test_without_cards_the_category_directions_stand_in_without_reordering(tmp_path):
    work = _work(tmp_path, [])
    design = asyncio.run(settle_directions(work, FLOORS, 5))
    assert [d["label"] for d in design["directions"]] == [f["label"] for f in FLOORS]
    assert all(d["home"] == [s["id"] for s in POOL] for d in design["directions"]), "PATTERN_SECTIONS orders nothing"
    applied = apply_direction(LANDING, design["directions"][0], design["pool"])
    assert applied["pages"][0]["sections"] == [{**POOL[0], "content": applied["pages"][0]["sections"][0]["content"]},
                                               *POOL[1:]]  # fmt: skip


def test_fact_pack_names_the_category_default_and_what_the_renderer_draws():
    text = fact_pack(FLOORS[0], 42, "dynamic")
    assert "Variation: 42" in text and FLOORS[0]["productType"] in text and "`collage`" in text
    assert "Unbounded" in text and "Why choose us" in text and "data pages" in text


@pytest.mark.parametrize(
    ("text", "phrase"),
    [("Explore Dishes", "Explore …"), ("Learn more", "Learn more"), ("Why choose us?", None), ("Book a table", None)],
)
def test_stock_phrases(text, phrase):
    assert stock_phrase(text) == phrase


# -- the UI's mirror -------------------------------------------------------------------------------------------------

MIRROR = REPO / "agent-ui" / "src" / "features" / "specs" / "lib" / "design-direction.ts"
RUNNER = """
import { readFileSync } from "node:fs";
const { applyDirection } = await import(process.argv[2]);
const cases = JSON.parse(readFileSync(process.argv[3], "utf8"));
process.stdout.write(JSON.stringify(cases.map((c) => applyDirection(c.spec, c.direction, c.pool))));
"""


def _mirror_cases() -> list[dict]:
    nested = copy.deepcopy(LANDING)
    services = nested["pages"][1]["sections"]
    nested["pages"][1]["sections"] = [{"id": "cols", "component": "Columns", "children": services}]
    edited = apply_direction(LANDING, filled(home=["hero", "services", "cta"]), POOL)
    edited["pages"][0]["sections"].insert(1, {"id": "mine", "component": "RichText", "content": {"body": "x"}})
    cards = [Card.model_validate(c) for c in fake_cards(SPA, 3, POOL)]
    kept, _ = card_directions(cards, FLOORS, POOL, [], 3, None)
    tracker_pool = home_pool(TRACKER)
    return [
        {"spec": LANDING, "direction": kept[0], "pool": POOL},
        {"spec": LANDING, "direction": kept[1], "pool": POOL},
        {"spec": edited, "direction": kept[2], "pool": POOL},
        {"spec": nested, "direction": filled(sectionForms={"Features": "ledger"}, rhythm="dividers"), "pool": POOL},
        {"spec": LANDING, "direction": FLOORS[0], "pool": None},
        {"spec": TRACKER, "direction": filled(home=["recent", "stats"]), "pool": tracker_pool},
    ]


@pytest.mark.skipif(shutil.which("node") is None, reason="needs Node 22.18+ (type stripping) for the UI's TypeScript")
def test_the_ui_applies_a_direction_exactly_like_the_agent(tmp_path):
    cases = _mirror_cases()
    (tmp_path / "cases.json").write_text(json.dumps(cases))
    (tmp_path / "run.mjs").write_text(RUNNER)
    run = subprocess.run(
        ["node", "--no-warnings", str(tmp_path / "run.mjs"), MIRROR.as_uri(), str(tmp_path / "cases.json")],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if run.returncode and "Unknown file extension" in run.stderr:
        pytest.skip("this Node cannot strip TypeScript types")
    assert run.returncode == 0, run.stderr
    ui = json.loads(run.stdout)
    for index, (case, mirrored) in enumerate(zip(cases, ui, strict=True)):
        agent = apply_direction(case["spec"], case["direction"], case["pool"])
        assert mirrored == agent, f"case {index}"
