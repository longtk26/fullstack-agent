"""Stories 17.1 (typed section props, layout nodes) and 17.2 (section renderer for static sites)."""

import copy
import json
import os
from pathlib import Path

from src.modules.shared.domain.frontend_spec import frontend_spec_json_schema, validate_frontend_spec_data
from src.orchestrator.frontend_codegen import generated_files
from src.orchestrator.frontend_planner import plan_frontend
from src.orchestrator.frontend_renderer import RENDERED, renderer_gaps, section_props_ts
from src.orchestrator.frontend_scaffold import OVERLAY_DIR, OWNED_INFO, scaffold_frontend
from tests.generation_helpers import EXAMPLES

FIXTURES = Path(__file__).parent / "fixtures"
LANDING = json.loads((EXAMPLES / "frontend-specs" / "static-landing.json").read_text())
LIBRARY = json.loads((FIXTURES / "frontend-specs" / "section-library.json").read_text())
LIBRARY_DIR = OVERLAY_DIR / "files" / "renderer" / "src" / "components" / "sections"


def issues(spec: dict) -> list[tuple[str, str, str]]:
    report = validate_frontend_spec_data(spec).report
    return [(i.severity, i.code, i.path) for i in report.errors + report.warnings]


def planned(spec: dict) -> dict:
    result = validate_frontend_spec_data(spec)
    assert result.report.valid, result.report.errors
    return plan_frontend(result.normalized)


# -- 17.1 typed content ------------------------------------------------------------------------------------------------


def test_section_content_is_checked_against_its_props_model():
    spec = copy.deepcopy(LANDING)
    hero = spec["pages"][0]["sections"][0]["content"]
    del hero["heading"]
    spec["pages"][3]["sections"][1]["content"]["items"][0]["value"] = ["40+"]
    spec["pages"][4]["sections"][0]["content"] = {"email": "not-an-email"}
    del spec["content"][1]["records"][0]["price"]  # the Pricing section shows `plans`
    found = issues(spec)
    assert ("error", "FE_INVALID_PROPS", "/pages/0/sections/0/content/heading") in found
    assert any(path.startswith("/pages/3/sections/1/content/items/0/value") for _, code, path in found)
    assert ("error", "FE_INVALID_PROPS", "/pages/4/sections/0/content/email") in found
    assert ("error", "FE_INVALID_PROPS", "/content/1/records/0/price") in found


def test_unknown_keys_are_warnings_and_list_sections_need_items():
    spec = copy.deepcopy(LANDING)
    spec["pages"][0]["sections"][0]["content"]["headline"] = "typo"
    spec["pages"][0]["sections"][0]["content"]["cta"]["colour"] = "red"
    del spec["pages"][3]["sections"][1]["content"]["items"]
    found = issues(spec)
    assert ("warning", "FE_UNKNOWN_PROP", "/pages/0/sections/0/content/headline") in found
    assert ("warning", "FE_UNKNOWN_PROP", "/pages/0/sections/0/content/cta/colour") in found
    assert ("error", "FE_INVALID_PROPS", "/pages/3/sections/1/content/items") in found


def test_a_redeclared_built_in_keeps_free_form_content():
    spec = copy.deepcopy(LANDING)
    spec["components"] = [{"name": "Hero", "kind": "composite", "description": "Our own hero"}]
    spec["pages"][0]["sections"][0]["content"] = {"anything": True}
    assert issues(spec) == []


def test_layout_nodes_hold_sections_three_levels_deep_at_most():
    spec = copy.deepcopy(LIBRARY)
    home = spec["pages"][0]["sections"]
    assert issues(spec) == []
    home[2]["children"][1]["children"][0] = {"id": "too-deep", "component": "Stack", "children": [home[0]]}
    home[3]["children"] = [{"id": "child", "component": "RichText", "content": {"body": "x"}}]
    spec["pages"][2]["sections"][1]["children"][0]["id"] = "tabs"  # same id as a top-level section
    spec["pages"][2]["sections"][0]["content"]["labels"] = ["Only one"]
    spec["pages"][1]["sections"].append({"id": "empty", "component": "Columns", "children": []})
    found = issues(spec)
    assert ("error", "FE_INVALID_LAYOUT", "/pages/0/sections/2/children/1/children/0/children/0") in found
    assert ("error", "FE_INVALID_LAYOUT", "/pages/0/sections/3/children") in found
    assert ("error", "FE_DUPLICATE_ID", "/pages/2/sections/1/children/0/id") in found
    assert ("error", "FE_INVALID_PROPS", "/pages/2/sections/0/content/labels") in found
    assert ("error", "FE_INVALID_LAYOUT", "/pages/1/sections/3/children") in found


def test_the_editor_schema_types_each_built_in_sections_content():
    schema = frontend_spec_json_schema()
    rules = {
        rule["if"]["properties"]["component"]["const"]: rule["then"] for rule in schema["$defs"]["Section"]["allOf"]
    }
    assert rules["Hero"] == {"properties": {"content": {"$ref": "#/$defs/HeroProps"}}}
    assert set(rules) == set(RENDERED) | {"Form", "DetailView"}
    hero = schema["$defs"]["HeroProps"]
    assert hero["required"] == ["heading"] and hero["additionalProperties"] is True  # unknown keys: warnings only
    assert schema["$defs"]["FeaturesProps"]["properties"]["items"]["anyOf"][0]["items"] == {
        "$ref": "#/$defs/FeatureItem"
    }
    assert schema["$defs"]["Section"]["properties"]["children"]["anyOf"][0]["items"] == {"$ref": "#/$defs/Section"}


def test_section_content_types_match_the_snapshot():
    """The TypeScript the section library compiles against, generated from the props models."""
    text = section_props_ts()
    assert text == section_props_ts()
    snapshot = FIXTURES / "section-props.ts"
    if os.environ.get("UPDATE_SNAPSHOTS") or not snapshot.exists():
        snapshot.write_text(text)
    assert text == snapshot.read_text(), "section props changed: review, then rerun with UPDATE_SNAPSHOTS=1"
    assert "export type THeroContent = {\n  heading: string;\n" in text
    assert "  price: string | number;\n" in text and "  items?: TFeatureItem[];\n" in text


# -- 17.2 renderer -----------------------------------------------------------------------------------------------------


def test_only_what_the_library_can_render_skips_the_engine():
    assert planned(LANDING)["rendering"] == "renderer" and planned(LIBRARY)["rendererGaps"] == []
    spec = copy.deepcopy(LANDING)
    spec["layout"]["shell"] = "sidebar"
    spec["components"] = [{"name": "Timeline", "description": "Our history"}]
    spec["pages"][3]["sections"].append({"id": "history", "component": "Timeline"})
    spec["forms"] = [{"id": "contact", "fields": [{"name": "email", "type": "email"}]}]
    spec["pages"][4]["sections"].append({"id": "form", "component": "Form", "form": "contact"})
    plan = planned(spec)
    assert plan["rendering"] == "engine"
    assert plan["rendererGaps"] == [  # the sidebar shell is in the library (17.4)
        "about/history: Timeline is not in the section library",
        "contact/form: forms without an operation (static forms)",
    ]
    assert renderer_gaps({"project": {"mode": "dynamic"}}, [], []) == []  # dynamic mode renders too (17.4)


def test_generated_files_hold_the_pages_as_data():
    plan = planned(LIBRARY)
    files = generated_files(plan, validate_frontend_spec_data(LIBRARY).normalized, None)
    site = json.loads(files["src/content/site.json"])
    tabs = site["pages"]["more"]["sections"][0]
    assert [child["component"] for child in tabs["children"]] == ["Features", "Faq", "Pricing"]
    assert tabs["children"][1]["data"]["collection"] == "faq"
    assert site["collections"]["products"][0]["name"] == "Blue mug"
    registry = files["src/components/renderer/registry.ts"]
    assert 'import { DataTable } from "@/components/sections/DataTable";' in registry
    assert "Form" not in registry
    page = files["src/app/catalogue/page.tsx"]
    assert 'export const metadata: Metadata = {"title": "Catalogue"};' in page
    assert '<PageRenderer pageId="catalogue" />' in page
    # The smoke test expects text a visitor sees on load: not the Faq inside the second tab.
    smoke = files["tests/e2e/smoke.spec.ts"]
    assert '"text": "Lovely."' in smoke and "Is it fast?" not in smoke


def test_the_library_covers_every_rendered_section():
    for name in RENDERED:
        assert (LIBRARY_DIR / f"{name}.tsx").is_file(), name


def test_a_site_gets_only_the_library_sections_it_uses(tmp_path):
    spec = validate_frontend_spec_data(LANDING).normalized
    plan = plan_frontend(spec)
    scaffold_frontend(tmp_path, plan, spec)
    sections = tmp_path / "src/components/sections"
    assert (sections / "Hero.tsx").is_file() and (sections / "CtaLink.tsx").is_file()
    assert not (sections / "DataTable.tsx").exists() and not (sections / "Tabs.tsx").exists()
    owned = json.loads((tmp_path / OWNED_INFO).read_text())
    for relative in (
        "src/components/sections/Hero.tsx",
        "src/components/layout/SiteShell.tsx",
        "src/components/renderer/SectionRenderer.tsx",
        "src/content/site.json",
        "src/app/services/page.tsx",
    ):
        assert relative in owned, relative
