"""Story 17.7: fonts that load, section variants and the design checklist rules the generator enforces."""

import copy
import json
import typing
from pathlib import Path

import pytest

from src.modules.shared.domain.frontend_spec import (
    FONTS,
    SECTION_PROPS,
    closest_font,
    frontend_spec_json_schema,
    iter_sections,
    validate_frontend_spec_data,
)
from src.modules.shared.domain.frontend_spec.section_props import Background, CardStyle, HeroVariant, Surface
from src.orchestrator.frontend_codegen import generated_files
from src.orchestrator.frontend_planner import plan_frontend
from src.orchestrator.frontend_scaffold import BASE_DIR, OVERLAY_DIR
from src.orchestrator.frontend_theme import OFF_BLACK, OFF_WHITE, build_theme, fonts_ts, globals_css, luminance
from src.sandbox.docker_sandbox import store_volume

FIXTURES = Path(__file__).parent / "fixtures"
LIBRARY = json.loads((FIXTURES / "frontend-specs" / "section-library.json").read_text())


def _theme(**overrides) -> dict:
    spec = copy.deepcopy(LIBRARY)
    spec["theme"] = {"style": "minimal", **overrides}
    return validate_frontend_spec_data(spec).normalized["theme"]


def _issues(spec: dict) -> list[tuple[str, str, str | None]]:
    report = validate_frontend_spec_data(spec).report
    return [(issue.code, issue.path, issue.hint) for issue in report.errors + report.warnings]


# -- fonts -------------------------------------------------------------------------------------------------------------


def test_every_bundled_font_is_pinned_in_the_frontend_base():
    dependencies = json.loads((BASE_DIR / "package.json").read_text())["dependencies"]
    assert 20 <= len(FONTS) <= 24
    for font in FONTS.values():
        assert dependencies.get(font.package, "").startswith("5."), font.package


@pytest.mark.parametrize(
    ("name", "suggestion"),
    [
        ("inter", "Inter"),
        ("Playfair", "Playfair Display"),
        ("Source Serif Pro", "Source Serif 4"),
        ("Fira Code", "JetBrains Mono"),
        ("Libre Baskerville", "Source Serif 4"),
        ("Merriweather Sans", "Inter"),
        ("Abril Fatface", "Playfair Display"),
    ],
)
def test_closest_bundled_font(name, suggestion):
    assert closest_font(name) == suggestion


def test_a_font_outside_the_set_is_a_warning_with_the_closest_one():
    spec = copy.deepcopy(LIBRARY)
    spec["theme"]["typography"] = {"headingFont": "Playfair", "bodyFont": "Lato"}
    result = validate_frontend_spec_data(spec)
    assert result.report.valid
    assert _issues(spec) == [
        ("FE_FONT_NOT_BUNDLED", "/theme/typography/headingFont", "Closest bundled font: Playfair Display"),
        ("FE_FONT_NOT_BUNDLED", "/theme/typography/bodyFont", "Closest bundled font: Inter"),
    ]


def test_the_editor_schema_lists_the_bundled_fonts():
    typography = frontend_spec_json_schema()["$defs"]["Typography"]["properties"]
    assert typography["headingFont"]["examples"] == list(FONTS)
    assert typography["bodyFont"]["examples"] == list(FONTS)


def test_theme_fonts_are_imported_from_their_packages():
    theme = build_theme(_theme(typography={"headingFont": "Space Grotesk", "bodyFont": "Atkinson Hyperlegible"}))
    source = fonts_ts(theme)
    assert 'import "@fontsource/space-grotesk/600.css";\n' in source
    assert 'import "@fontsource/atkinson-hyperlegible/700.css";\n' in source
    assert "atkinson-hyperlegible/500.css" not in source  # only the weights the family has
    assert theme["fonts"]["heading"].startswith('"Space Grotesk", ui-sans-serif')


def test_unbundled_fonts_only_name_the_family_and_mono_falls_back_to_mono():
    theme = build_theme(_theme(typography={"headingFont": "Fira Code", "bodyFont": "Lato"}))
    assert theme["fonts"]["imports"] == []
    assert "not in the bundled set" in fonts_ts(theme) and "export {};" in fonts_ts(theme)
    assert theme["fonts"]["heading"] == '"Fira Code", ui-monospace, "SF Mono", Menlo, Consolas, monospace'


def test_every_generated_site_loads_its_fonts_from_the_root_layout():
    plan = plan_frontend(validate_frontend_spec_data(LIBRARY).normalized)
    files = generated_files(plan, validate_frontend_spec_data(LIBRARY).normalized, None)
    assert "@fontsource/poppins/400.css" in files["src/app/fonts.ts"]  # the playful preset: Poppins + Nunito
    layout = (OVERLAY_DIR / "files" / "common" / "src" / "app" / "layout.tsx").read_text()
    assert 'import "./fonts";\n' in layout


def test_the_store_volume_follows_the_base_lock(tmp_path):
    lock = tmp_path / "pnpm-lock.yaml"
    lock.write_text("one")
    first = store_volume("bga-pnpm-store", lock)
    lock.write_text("two")
    assert first.startswith("bga-pnpm-store-") and store_volume("bga-pnpm-store", lock) != first
    assert store_volume("bga-pnpm-store", tmp_path / "missing") == "bga-pnpm-store"


# -- design checklist rules in the theme -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "overrides",
    [
        {"colorScheme": "light-dark"},
        {"colorScheme": "dark", "colors": {"background": "#000000", "foreground": "#ffffff"}},
        {"colorScheme": "light-dark", "colors": {"background": "#ffffff", "foreground": "#000000"}},
    ],
)
def test_dark_mode_uses_off_black_and_off_white(overrides):
    theme = build_theme(_theme(**overrides))
    dark = theme["dark"]
    assert luminance(dark["background"]) >= luminance(OFF_BLACK)
    assert luminance(dark["foreground"]) <= luminance(OFF_WHITE)


def test_a_primary_section_swaps_the_tokens_in_light_and_dark():
    theme = build_theme(_theme(colorScheme="light-dark"))
    css = globals_css(theme)
    assert ".surface-inverse {\n" in css and ".dark .surface-inverse {\n" in css
    inverse = css.split(".surface-inverse {\n", 1)[1].split("}", 1)[0]
    assert f"  --background: {theme['light']['primary']};" in inverse
    assert f"  --primary: {theme['light']['primary-foreground']};" in inverse


# -- section variants --------------------------------------------------------------------------------------------------


def _hero(**content) -> dict:
    spec = copy.deepcopy(LIBRARY)
    spec["pages"][0]["sections"][0]["content"] |= content
    return spec


def test_an_image_background_needs_its_image():
    assert ("FE_INVALID_PROPS", "/pages/0/sections/0/content", None) in _issues(_hero(background="image"))
    assert _issues(_hero(background="image", backgroundImage="asset:work")) == []


def test_variants_are_typed():
    assert _issues(_hero(variant="fullscreen"))[0][:2] == ("FE_INVALID_PROPS", "/pages/0/sections/0/content/variant")
    assert _issues(_hero(variant="banner", background="primary")) == []


def test_a_long_hero_headline_is_a_design_warning():
    issues = _issues(_hero(heading="A headline that goes on and on past the two lines a phone can show"))
    assert issues == [
        (
            "FE_DESIGN_RULE",
            "/pages/0/sections/0/content/heading",
            "Keep it to 50 characters or fewer and move the rest into 'body'",
        )
    ]


def test_the_section_library_fixture_covers_every_variant():
    sections = [section for page in LIBRARY["pages"] for section in iter_sections(page["sections"])]
    used = {
        (s["component"], key, s["content"][key])
        for s in sections
        for key in ("background", "variant", "cardStyle")
        if key in (s.get("content") or {})
    }
    for values, key in ((Background, "background"), (HeroVariant, "variant"), (CardStyle, "cardStyle")):
        assert set(typing.get_args(values)) <= {value for _, k, value in used if k == key}, key
    for name, model in SECTION_PROPS.items():
        default = model.model_fields
        if issubclass(model, Surface):
            assert any(c == name and k == "background" and v != default["background"].default for c, k, v in used), name
        if "card_style" in default:
            assert any(c == name and k == "cardStyle" and v != "outline" for c, k, v in used), name
