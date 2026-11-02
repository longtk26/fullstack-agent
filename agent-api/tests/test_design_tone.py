"""Tone tokens (Story 20.3): the tone → token table, the tokens in globals.css, the colour roles they give a page."""

import copy
import json
from pathlib import Path

import pytest

from src.modules.shared.domain.frontend_spec import validate_frontend_spec_data
from src.orchestrator.design_tone import apply_tone, normalize_tone, tone_tokens
from src.orchestrator.frontend_planner import plan_frontend
from src.orchestrator.frontend_renderer import color_roles, site_json
from src.orchestrator.frontend_theme import build_theme, globals_css

EXAMPLES = Path(__file__).parents[2] / "examples"
LANDING = json.loads((EXAMPLES / "frontend-specs" / "static-landing.json").read_text())


def _tone(energy=3, finish=3, density=3, weight=3, seriousness=3) -> dict:
    return {"energy": energy, "finish": finish, "density": density, "weight": weight, "seriousness": seriousness}


def test_the_neutral_tone_is_today_with_one_anchor_section():
    assert tone_tokens(_tone()) == {
        "colorArea": "block",
        "surface": "outline",
        "radius": "md",
        "density": "comfortable",
        "typography": {"headingWeight": 600, "headingCase": "normal", "tracking": "normal", "ratio": "default"},
    }


@pytest.mark.parametrize(
    ("tone", "expected"),
    [
        (_tone(energy=1), {"colorArea": "minimal", "typography.ratio": "tight"}),
        (_tone(energy=2), {"colorArea": "minimal", "typography.ratio": "default"}),
        (_tone(energy=5), {"colorArea": "bold", "typography.ratio": "dramatic", "typography.tracking": "tight"}),
        (_tone(finish=1), {"radius": "none", "surface": "outline"}),
        (_tone(finish=5, weight=4), {"surface": "raised", "typography.headingWeight": 700}),
        (_tone(finish=5, weight=2), {"surface": "flat", "typography.headingWeight": 500}),
        (_tone(seriousness=1), {"radius": "lg"}),
        (_tone(seriousness=5), {"radius": "sm", "typography.headingCase": "normal"}),
        (_tone(seriousness=4, energy=4), {"typography.headingCase": "upper", "typography.tracking": "wide"}),
        (_tone(density=4), {"density": "compact"}),
        (_tone(weight=1), {"typography.headingWeight": 400, "typography.tracking": "normal"}),
    ],
)
def test_each_scale_moves_its_tokens(tone, expected):
    tokens = tone_tokens(tone)
    flat = {**{k: v for k, v in tokens.items() if k != "typography"}}
    flat |= {f"typography.{k}": v for k, v in tokens["typography"].items()}
    assert {key: flat[key] for key in expected} == expected


def test_missing_or_bad_values_count_as_neutral_and_are_clamped():
    assert normalize_tone({"energy": 9, "finish": "x", "weight": 0}) == _tone(energy=5, weight=1)
    assert tone_tokens(None) == tone_tokens(_tone())


def test_apply_tone_keeps_fonts_and_colours():
    theme = {"style": "editorial", "colors": {"primary": "#123456"}, "typography": {"headingFont": "Fraunces"}}
    applied = apply_tone(theme, _tone(energy=5, finish=1))
    assert applied["colors"] == {"primary": "#123456"} and applied["style"] == "editorial"
    assert applied["typography"]["headingFont"] == "Fraunces" and applied["typography"]["ratio"] == "dramatic"
    assert applied["radius"] == "none" and applied["colorArea"] == "bold"


def _validated(spec: dict) -> dict:
    result = validate_frontend_spec_data(spec)
    assert result.report.valid, result.report.errors
    return result.normalized


def test_every_tone_gives_a_valid_theme():
    for energy in (1, 3, 5):
        for finish in (1, 3, 5):
            for weight in (1, 3, 5):
                spec = copy.deepcopy(LANDING)
                spec["theme"] = apply_tone(spec["theme"], _tone(energy=energy, finish=finish, weight=weight))
                _validated(spec)


def test_tokens_in_globals_css():
    plain = globals_css(build_theme(_validated(LANDING)["theme"]))
    # Without tokens: today's semibold headings with tight tracking, Tailwind's type scale, the Card's own ring.
    assert "--heading-weight: 600;" in plain and "--heading-tracking: -0.025em;" in plain
    assert "--heading-case: none;" in plain and "@utility heading {" in plain
    assert "--text-5xl" not in plain and '[data-slot="card"]' not in plain
    spec = copy.deepcopy(LANDING)
    spec["theme"] = apply_tone(spec["theme"], _tone(energy=5, finish=5, weight=5, seriousness=5))
    loud = globals_css(build_theme(_validated(spec)["theme"]))
    assert "--heading-weight: 700;" in loud and "--heading-case: uppercase;" in loud
    assert "--heading-tracking: 0.06em;" in loud and "--text-5xl: 3.5rem;" in loud
    assert '[data-slot="card"]:not(.ring-0) {' in loud
    spec["theme"]["surface"] = "flat"
    assert '[data-slot="card"] {\n  box-shadow: none;' in globals_css(build_theme(_validated(spec)["theme"]))


def _sections(*components: str, **backgrounds: str) -> list[dict]:
    return [
        {"id": f"s{i}", "component": c, "content": {"background": backgrounds[c]} if c in backgrounds else {}}
        for i, c in enumerate(components)
    ]


def _backgrounds(sections: list[dict]) -> list[str | None]:
    return [(section.get("content") or {}).get("background") for section in sections]


def test_color_roles():
    page = _sections("Hero", "Features", "CallToAction", "Faq", "CallToAction")
    assert _backgrounds(color_roles(page, None)) == [None] * 5
    assert _backgrounds(color_roles(page, "minimal")) == [None, None, "muted", None, "muted"]
    assert _backgrounds(color_roles(page, "block")) == [None, None, "primary", None, "muted"]
    assert _backgrounds(color_roles(page, "bold")) == ["primary", None, "primary", None, "muted"]
    # No call to action: the last content section is the anchor; a background the spec names is kept.
    page = _sections("Hero", "Features", "ContactInfo", Hero="muted")
    assert _backgrounds(color_roles(page, "bold")) == ["muted", None, "primary"]
    # A section the spec already puts on the primary colour is the anchor: no second one.
    page = _sections("Hero", "Team", "Statement", Statement="primary")
    assert _backgrounds(color_roles(page, "block")) == [None, None, "primary"]


def test_color_area_reaches_site_json():
    spec = copy.deepcopy(LANDING)
    spec["theme"]["colorArea"] = "minimal"
    normalized = _validated(spec)
    home = json.loads(site_json(plan_frontend(normalized), normalized))["pages"]["home"]
    cta = next(section for section in home["sections"] if section["component"] == "CallToAction")
    assert cta["content"]["background"] == "muted"


def test_wide_faces_and_capitals_shrink_the_hero_sizes():
    from src.orchestrator.frontend_theme import display_scale, hero_vars

    assert display_scale("Inter", {}) == 1.0 and display_scale("Playfair Display", {"tracking": "tight"}) == 1.0
    assert 0.85 < display_scale("Montserrat", {}) < 0.95
    assert display_scale("Unbounded", {"headingCase": "upper"}) == 0.559
    assert display_scale("Space Mono", {"headingCase": "upper", "tracking": "wide"}) >= 0.55, "never below the floor"
    assert display_scale("Syne", {"headingCase": "upper"}) < display_scale("Syne", {}) < 1
    assert hero_vars({}, 1.0)[2] == "  --hero-4xl: 2.25rem;", "Tailwind's step without tokens"
    dramatic = hero_vars({"ratio": "dramatic"}, 0.5)
    assert dramatic[2] == "  --hero-4xl: 1.125rem;", "longer headlines keep their size (Story 20.4)"
    assert dramatic[4] == "  --hero-6xl: 2.25rem;", "short ones grow with the ratio"
    assert hero_vars({"ratio": "tight"}, 1.0)[2] == "  --hero-4xl: 2rem;", "a tight ratio shrinks every step"


def test_the_display_scale_reaches_globals_css_only_when_it_shrinks():
    plain = build_theme(_validated(LANDING)["theme"])
    assert "displayScale" not in plain and "--hero-6xl: 3.75rem;" in globals_css(plain)
    spec = copy.deepcopy(LANDING)
    spec["theme"]["typography"] = {"headingFont": "Unbounded", "headingCase": "upper"}
    wide = build_theme(_validated(spec)["theme"])
    assert wide["displayScale"] == 0.559 and "--hero-6xl: 2.096rem;" in globals_css(wide)
