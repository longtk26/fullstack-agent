"""Design diversity measures (Story 20.1): visual fields, the difference test, section and copy measures, and the
first-screen similarity of screenshots."""

import copy
import json
from pathlib import Path

import pytest
from PIL import Image

from src.orchestrator import design_diversity as dd

EXAMPLES = Path(__file__).parents[2] / "examples"
LANDING = json.loads((EXAMPLES / "frontend-specs" / "static-landing.json").read_text())


@pytest.mark.parametrize(
    ("color", "family"),
    [
        ("#dc2626", "h0"),
        ("#0ea5e9", "h180"),
        ("#7c3aed", "h240"),
        ("#18181b", "neutral"),
        ("#ffffff", "neutral"),
        ("#808080", "neutral"),
        ("not a colour", "neutral"),
        (None, "neutral"),
    ],
)
def test_hue_family_buckets_hues_and_calls_greys_neutral(color, family):
    assert dd.hue_family(color) == family


def _with_hero(**content) -> dict:
    spec = copy.deepcopy(LANDING)
    hero = spec["pages"][0]["sections"][0]
    hero["content"] = {"heading": "Hello", **content}
    return spec


def test_visual_fields_of_the_golden_landing_page():
    # editorial preset: no font in the spec, so the preset's heading font counts; no primary, so the preset's.
    assert dd.visual_fields(LANDING) == {
        "hero": "split",
        "headingFont": "Playfair Display",
        "hueFamily": "neutral",
        "keyVisual": "illustration",
    }
    assert dd.home_sections(LANDING) == ["Hero", "Features", "Testimonials", "CallToAction"]


def test_key_visual_names_what_carries_the_first_screen():
    assert dd.key_visual(_with_hero()) == "type"
    assert dd.key_visual(_with_hero(image="https://example.com/a.jpg")) == "image"
    assert dd.key_visual(_with_hero(image="asset:work-2")) == "image"  # a placeholder image
    photo = _with_hero(image="asset:hero")
    photo["assets"][0].update(source="upload:upl_1", prompt="a lake at dawn")
    assert dd.key_visual(photo) == "photo"
    no_hero = copy.deepcopy(LANDING)
    no_hero["pages"][0]["sections"] = no_hero["pages"][0]["sections"][1:]
    assert dd.key_visual(no_hero) == "none" and dd.visual_fields(no_hero)["hero"] == "none"


def test_layout_nodes_are_skipped_but_their_children_count():
    spec = copy.deepcopy(LANDING)
    sections = spec["pages"][0]["sections"]
    spec["pages"][0]["sections"] = [sections[0], {"id": "row", "component": "Columns", "children": sections[1:3]}]
    assert dd.home_sections(spec) == ["Hero", "Features", "Testimonials"]


FIELDS = [
    {"hero": "split", "headingFont": "Inter", "hueFamily": "h0", "keyVisual": "photo"},
    {"hero": "type", "headingFont": "Fraunces", "hueFamily": "h210", "keyVisual": "type"},
    {"hero": "banner", "headingFont": "Syne", "hueFamily": "neutral", "keyVisual": "photo"},
]
HOMES = [["Hero", "Features", "CallToAction"], ["Hero", "Steps", "Team"], ["Hero", "Features", "CallToAction"]]
DEFAULT = ["Hero", "Features", "Testimonials", "CallToAction"]


def test_distinct_directions_pass_the_difference_test():
    assert dd.difference_problems(FIELDS, HOMES, DEFAULT) == []


def test_the_difference_test_names_each_problem():
    fields = copy.deepcopy(FIELDS)
    fields[2].update(hero="split", headingFont="Inter")
    problems = dd.difference_problems(fields, [HOMES[0]] * 3, DEFAULT)
    assert problems == [
        "directions 1 and 3 share hero, headingFont, keyVisual",
        "2 directions use the split hero",
        "every home page follows the category's default order",
    ]


def test_off_default_compares_the_opening_sections():
    assert not dd.off_default(["Hero", "Features", "CallToAction"], DEFAULT)
    assert dd.off_default(["Hero", "Testimonials", "Features"], DEFAULT)
    assert dd.off_default(["Statement", "Hero", "Features"], DEFAULT)


def test_distinct_triples_and_pair_distance():
    assert dd.distinct_triples(FIELDS + [dict(FIELDS[0], keyVisual="type")]) == 3
    assert dd.pair_distance(FIELDS[0], FIELDS[1]) == 4
    assert dd.pair_distance(FIELDS[0], FIELDS[2]) == 3


def test_section_frequency_jaccard_and_repeated_copy():
    other = copy.deepcopy(LANDING)
    other["pages"] = [page for page in other["pages"] if page["route"] in ("/", "/contact")]
    frequency = dd.section_frequency([LANDING, other])
    assert frequency["Hero"] == 1.0 and frequency["Faq"] == 0.5
    assert dd.jaccard({"Hero", "Faq"}, {"Hero", "Steps"}) == pytest.approx(0.333)
    assert dd.jaccard(set(), set()) == 1.0
    repeated = dd.repeated_copy([LANDING, other])
    assert repeated["see our work"] == 2 and repeated["design that sounds like you"] == 2
    assert all(count > 1 for count in repeated.values())


def _png(path: Path, colour: int, height: int = 1200) -> Path:
    image = Image.new("L", (1440, height), colour)
    image.paste(255 - colour, (0, 0, 720, 900))  # the left half of the first screen is inverted
    image.save(path)
    return path


def test_first_screen_similarity(tmp_path):
    light = dd.first_screen(_png(tmp_path / "a.png", 255))
    same = dd.first_screen(_png(tmp_path / "b.png", 255, height=3000))  # below the first screen does not count
    dark = dd.first_screen(_png(tmp_path / "c.png", 0))
    assert len(light) == dd.THUMBNAIL[0] * dd.THUMBNAIL[1]
    assert dd.image_similarity(light, same) == 1.0
    assert dd.image_similarity(light, dark) == 0.0
    with pytest.raises(ValueError):
        dd.image_similarity(light, light[:-1])
