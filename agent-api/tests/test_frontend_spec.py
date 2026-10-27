"""FrontendSpec 1.0 (Story 12.1): schema, semantic codes, normalizer."""

import copy
import json
from pathlib import Path

import pytest

from src.modules.shared.domain.frontend_spec import (
    THEME_PRESETS,
    frontend_spec_json_schema,
    validate_frontend_spec_data,
    validate_frontend_spec_text,
)

EXAMPLES = Path(__file__).parents[2] / "examples" / "frontend-specs"
SHOP = json.loads((EXAMPLES / "shop-dynamic.json").read_text())
LANDING = json.loads((EXAMPLES / "static-landing.json").read_text())


def codes(spec: dict) -> list[tuple[str, str]]:
    report = validate_frontend_spec_data(spec).report
    return [(issue.code, issue.path) for issue in [*report.errors, *report.warnings]]


@pytest.mark.parametrize("path", sorted(EXAMPLES.glob("*.json")), ids=lambda p: p.name)
def test_examples_are_valid_without_warnings(path):
    result = validate_frontend_spec_text(path.read_text())
    assert result.report.valid, result.report.errors
    assert result.report.warnings == []


def test_json_schema_is_exported_with_camel_case_names():
    schema = frontend_spec_json_schema()
    assert schema["$id"].endswith("frontend-spec-1.0.json")
    assert schema["title"] == "FrontendSpec 1.0"
    assert {"specVersion", "project", "theme", "layout", "pages", "components", "forms", "content", "assets"} <= set(
        schema["properties"]
    )
    assert "x-backendSpec" in schema["properties"]
    page = schema["$defs"]["Page"]
    assert page["additionalProperties"] is False and "route" in page["required"]


def test_malformed_json_and_unknown_version():
    assert validate_frontend_spec_text(b'{"specVersion": ').report.errors[0].code == "JSON_MALFORMED"
    assert codes({"specVersion": "9"}) == [("SPEC_VERSION_UNSUPPORTED", "/specVersion")]


def test_schema_violations_point_at_the_field():
    spec = copy.deepcopy(SHOP)
    spec["pages"][0]["route"] = "/Products"
    spec["pages"][1]["sections"][0]["colour"] = "red"
    spec["layout"]["header"]["navigation"][0] = {"label": "Shop"}
    found = codes(spec)
    assert ("SCHEMA_VIOLATION", "/pages/0/route") in found
    assert ("SCHEMA_VIOLATION", "/pages/1/sections/0/colour") in found
    assert ("SCHEMA_VIOLATION", "/layout/header/navigation/0") in found


def _mutate(spec: dict, change) -> dict:
    spec = copy.deepcopy(spec)
    change(spec)
    return spec


CASES = [
    (
        "FE_DUPLICATE_ROUTE",
        "/pages/3/route",
        lambda s: s["pages"][3].update(route="/products/[slug]"),
    ),
    ("FE_DUPLICATE_ID", "/pages/1/id", lambda s: s["pages"][1].update(id="home")),
    ("FE_DUPLICATE_ID", "/pages/0/sections/1/id", lambda s: s["pages"][0]["sections"][1].update(id="hero")),
    (
        "FE_UNKNOWN_COMPONENT",
        "/pages/1/sections/0/component",
        lambda s: s["pages"][1]["sections"][0].update(component="Carousel3d"),
    ),
    ("FE_UNKNOWN_COMPONENT", "/components/0/uses/0", lambda s: s["components"][0]["uses"].__setitem__(0, "fancy-card")),
    (
        "FE_UNKNOWN_PAGE",
        "/layout/header/navigation/0/page",
        lambda s: s["layout"]["header"]["navigation"][0].update(page="shop"),
    ),
    (
        "FE_UNKNOWN_PAGE",
        "/pages/0/sections/0/content/cta/page",
        lambda s: s["pages"][0]["sections"][0]["content"]["cta"].update(page="catalogue"),
    ),
    ("FE_UNKNOWN_PAGE", "/forms/0/onSuccess/navigate", lambda s: s["forms"][0]["onSuccess"].update(navigate="/basket")),
    ("FE_UNKNOWN_FORM", "/pages/2/sections/1/form", lambda s: s["pages"][2]["sections"][1].update(form="buy")),
    (
        "FE_UNKNOWN_ASSET",
        "/pages/0/sections/0/content/image",
        lambda s: s["pages"][0]["sections"][0]["content"].update(image="asset:missing"),
    ),
    (
        "FE_UNKNOWN_CONTENT",
        "/pages/5/sections/1/data/collection",
        lambda s: s["pages"][5]["sections"][1]["data"].update(collection="reviews"),
    ),
    (
        "FE_ROUTE_PARAM_UNBOUND",
        "/pages/1/sections/0/data/params",
        lambda s: s["pages"][1]["sections"][0]["data"]["params"].update(category="$route.category"),
    ),
    (
        "FE_ROUTE_PARAM_UNBOUND",
        "/pages/4/sections/1/form",
        lambda s: s["forms"][1]["fields"][0].update(value="$route.id"),
    ),
    (
        "FE_ROUTE_PARAM_UNBOUND",
        "/layout/footer/links/0/page",
        lambda s: s["layout"]["footer"]["links"][0].update(page="product-detail"),
    ),
    ("FE_INVALID_COLOR", "/theme/colors/primary", lambda s: s["theme"]["colors"].update(primary="blue-ish")),
    ("FE_STATIC_HAS_BINDING", "/pages/1/sections/0/data/operationId", lambda s: s["project"].update(mode="static")),
    ("FE_STATIC_HAS_BINDING", "/forms/0/operationId", lambda s: s["project"].update(mode="static")),
]


@pytest.mark.parametrize(("code", "path", "change"), CASES, ids=[f"{c}:{p}" for c, p, _ in CASES])
def test_semantic_errors_have_stable_codes(code, path, change):
    report = validate_frontend_spec_data(_mutate(SHOP, change)).report
    assert not report.valid
    assert (code, path) in [(issue.code, issue.path) for issue in report.errors]


def test_warnings_do_not_invalidate():
    spec = _mutate(LANDING, lambda s: s["theme"]["colors"].update(foreground="#cccccc", background="#ffffff"))
    spec["pages"][0]["route"] = "/start"
    spec["auth"] = {"login": True}
    report = validate_frontend_spec_data(spec).report
    assert report.valid
    assert {issue.code for issue in report.warnings} == {"FE_LOW_CONTRAST", "FE_NO_HOME_PAGE", "FE_UNSUPPORTED_FEATURE"}


def test_normalizer_fills_preset_page_ids_components_and_states():
    normalized = validate_frontend_spec_data(SHOP).normalized
    theme = normalized["theme"]
    preset = THEME_PRESETS["minimal"]["colors"]
    assert theme["colors"]["primary"] == "#1d4ed8"  # declared values win
    assert theme["colors"]["background"] == preset["background"] and theme["colors"]["muted"] == preset["muted"]
    assert [page["id"] for page in normalized["pages"]] == [
        "home", "products", "product-detail", "cart", "contact", "about",
    ]  # fmt: skip
    assert normalized["pages"][0]["seo"]["title"] == "Home"
    components = {component["name"]: component for component in normalized["components"]}
    assert components["Hero"] == {
        "name": "Hero",
        "kind": "section",
        "uses": ["button"],
        "description": "Heading, text, image and a call to action",
    }
    assert components["ProductGrid"]["kind"] == "composite"  # declared ones are kept as declared
    assert normalized["pages"][1]["sections"][0]["states"] == {
        "loading": "Loading…",
        "empty": "No products yet",
        "error": "Could not load products",
    }
    assert normalized["forms"][1]["submitLabel"] == "Send"
    assert normalized["project"]["locales"] == ["en"]


def test_static_preset_applies_editorial_tokens():
    normalized = validate_frontend_spec_data(LANDING).normalized
    assert normalized["theme"]["typography"]["headingFont"] == "Playfair Display"
    assert normalized["theme"]["radius"] == "sm"  # declared
    assert normalized["theme"]["density"] == "comfortable"  # from the preset
    assert normalized["layout"]["header"]["logoText"] == "Northwind"
