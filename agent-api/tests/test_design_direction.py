"""Story 12.6: design directions from UI UX Pro Max's data (vendored), ranked for a requirement, applied to a spec."""

import json
import re

import pytest

from src.modules.shared.domain.frontend_spec import FONTS, validate_frontend_spec_data
from src.orchestrator.design_direction import (
    DATA_DIR,
    apply_direction,
    contrast_failures,
    design_data,
    design_notes,
    directions,
    pick,
    reorder_sections,
    requirement_lead,
    with_brand,
)
from tests.generation_helpers import EXAMPLES

LANDING = json.loads((EXAMPLES / "frontend-specs" / "static-landing.json").read_text())
REQUIREMENTS = {
    "spa": "A day spa in Leeds offering massages, facials and wellness treatments. Clients book a treatment and "
    "see prices.",
    "restaurant": "Website for our Italian restaurant: menu, opening hours, reservations and location.",
    "saas": "Landing page for a B2B SaaS tool that automates invoicing for small businesses, with pricing tiers and a "
    "free trial.",
    "shop": "An online shop selling handmade ceramic mugs and plates, with product listings and a cart.",
    "portfolio": "A portfolio for a freelance photographer showing projects, an about page and contact details.",
}


def test_the_design_data_is_vendored_with_its_licence_and_pin():
    source = json.loads((DATA_DIR / "SOURCE.json").read_text())
    assert re.fullmatch(r"[0-9a-f]{40}", source["commit"]) and source["license"] == "MIT"
    assert "MIT License" in (DATA_DIR / "LICENSE").read_text()
    assert sorted(path.name for path in DATA_DIR.glob("*.csv")) == sorted(source["files"])
    assert not list(DATA_DIR.glob("*.py")), "only data is vendored, never the project's scripts"
    data = design_data()
    assert len(data.products) == len(data.colors) == len(data.reasoning) > 150
    assert data.source == f"ui-ux-pro-max@{source['commit'][:12]}"


# Stable product type, palette (primary) and home order per kind of site: re-check after `make design-data`.
@pytest.mark.parametrize(
    ("kind", "product", "primary", "order", "hero"),
    [
        ("spa", "Beauty/Spa/Wellness Service", "#ec4899",
         ["Hero", "Features", "Testimonials", "Stats", "CallToAction", "ContactInfo"], "banner"),
        ("restaurant", "Restaurant/Food Service", "#dc2626",
         ["Hero", "Features", "Pricing", "Faq", "CallToAction", "ContactInfo"], "banner"),
        ("saas", "SaaS (General)", "#2563eb", ["Hero", "Features", "CallToAction", "ContactInfo"], "split"),
        ("shop", "E-commerce", "#059669", ["Hero", "Features", "Stats", "CallToAction", "ContactInfo"], "split"),
        ("portfolio", "Portfolio/Personal", "#18181b",
         ["Hero", "RichText", "Gallery", "CallToAction", "ContactInfo"], "banner"),
    ],
)  # fmt: skip
def test_each_kind_of_site_gets_a_stable_direction(kind, product, primary, order, hero):
    found = directions(REQUIREMENTS[kind])
    assert len(found) == 3 and len({item["label"] for item in found}) == 3
    best = found[0]
    assert (best["productType"], best["theme"]["colors"]["primary"]) == (product, primary)
    assert (best["homeOrder"], best["heroVariant"]) == (order, hero)
    assert best["theme"]["direction"]["source"].startswith("ui-ux-pro-max@")


@pytest.mark.parametrize("kind", sorted(REQUIREMENTS))
def test_every_direction_passes_the_contrast_checks_and_uses_bundled_fonts(kind):
    for item in directions(REQUIREMENTS[kind]):
        assert contrast_failures(item["theme"]) == [], item["label"]
        typography = item["theme"]["typography"]
        assert typography["headingFont"] in FONTS and typography["bodyFont"] in FONTS
        assert item["theme"]["style"] in ("minimal", "editorial", "playful", "corporate", "dashboard")


def test_a_direction_that_fails_contrast_is_skipped():
    data = design_data()
    failing = [
        i for i in range(len(data.products)) if contrast_failures(directions.__globals__["direction"](i)["theme"])
    ]
    assert failing, "the data has palettes our derived tokens reject"
    name = data.products[failing[0]]["Product Type"]
    assert name not in [item["productType"] for item in directions(name)]


def test_alternatives_are_related_product_types_or_variations_of_the_best():
    shop = [item["label"] for item in directions(REQUIREMENTS["shop"])]
    assert shop == ["E-commerce", "E-commerce Luxury", "Marketplace (P2P)"]
    spa = directions(REQUIREMENTS["spa"])
    assert [item["productType"] for item in spa] == ["Beauty/Spa/Wellness Service"] * 3
    assert len({(item["theme"]["style"], item["heroVariant"]) for item in spa}) == 3
    assert directions("zzz qqq")[0]["productType"], "a requirement that matches nothing still gets a direction"


def test_the_lead_of_a_markdown_requirement_decides():
    text = (
        "# Northwind Studio — a design studio\n\n**Mode:** static\n\nNorthwind is a small brand studio.\n\n## Pages\n"
    )
    assert requirement_lead(text) == "Northwind Studio — a design studio\nNorthwind is a small brand studio."


def test_applying_a_direction_fills_the_theme_and_orders_the_home_page():
    chosen = directions(REQUIREMENTS["restaurant"])[0]
    spec = json.loads(json.dumps(LANDING))
    spec["theme"]["colorScheme"] = "light-dark"
    out = apply_direction(spec, chosen)
    assert out["theme"]["colors"] == chosen["theme"]["colors"] and out["theme"]["colorScheme"] == "light-dark"
    home = next(page for page in out["pages"] if page["route"] == "/")
    components = [section["component"] for section in home["sections"]]
    assert components[0] == "Hero" and components.index("Features") < components.index("CallToAction")
    assert home["sections"][0]["content"]["variant"] == "banner"
    result = validate_frontend_spec_data(out)
    assert result.report.valid and not [w for w in result.report.warnings if w.code == "FE_FONT_NOT_BUNDLED"]
    assert spec["theme"] != out["theme"], "the input spec is not changed"


def test_other_sections_stay_after_the_one_they_followed():
    sections = [{"component": name} for name in ("Custom", "CallToAction", "Hero", "Gallery", "Features", "Map")]
    order = [s["component"] for s in reorder_sections(sections, ["Hero", "Features", "CallToAction"])]
    assert order == ["Custom", "Hero", "Gallery", "Features", "Map", "CallToAction"]


def test_brand_colours_and_fonts_win_and_the_named_brief_is_picked():
    found = directions(REQUIREMENTS["shop"])
    branded = with_brand(found[1], {"colors": {"primary": "#0A7", "nope": "#000"}, "fonts": {"headingFont": "Lora"}})
    assert branded["theme"]["colors"]["primary"] == "#0a7" and "nope" not in branded["theme"]["colors"]
    assert branded["theme"]["typography"]["headingFont"] == "Lora" and found[1]["theme"]["colors"]["primary"] != "#0a7"
    assert pick(found, "e-commerce luxury") == 1 and pick(found, "Something else") == 0 and pick(found, None) == 0


def test_design_notes_explain_the_look():
    notes = design_notes(directions(REQUIREMENTS["saas"])[0])
    assert notes[0]["message"].startswith("Design direction: SaaS (General)") and notes[0]["path"] == "/theme"
    assert any(note["message"].startswith("Avoid: ") for note in notes)
