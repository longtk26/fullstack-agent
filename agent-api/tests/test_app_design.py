"""The design brief completed by code (Epic 23): archetypes and their frames (23.2), field roles and views checked
against the data (23.3–23.5), looks (23.7) and areas (23.10). Pure functions, no model call."""

import json
from pathlib import Path

import pytest

from src.modules.shared.domain.backend_spec import validate_spec_data
from src.modules.shared.domain.frontend_spec import validate_frontend_spec_data
from src.modules.shared.domain.frontend_spec.app import outline_schema
from src.orchestrator.backend.planner import build_plan
from src.orchestrator.frontend.app.design import ARCHETYPES, archetype_for, complete_design, kit_design
from src.orchestrator.frontend.app.files import app_data
from src.orchestrator.frontend.app.outline import complete_outline
from src.orchestrator.frontend.app.screens import app_frontend_spec, ensure_aggregates
from src.orchestrator.frontend.planner import plan_frontend
from src.orchestrator.integration.contract import build_contract

EXAMPLES = Path(__file__).parents[2] / "examples"
KIT = (
    Path(__file__).parents[1]
    / "templates"
    / "nextjs_overlay"
    / "files"
    / "dynamic"
    / "app"
    / "src"
    / "components"
    / "app"
)


def _backend(name: str) -> dict:
    return validate_spec_data(json.loads((EXAMPLES / "specs" / f"{name}.json").read_text())).normalized


@pytest.mark.parametrize(
    ("name", "archetype"),
    [
        ("news-feed", "feed"),
        ("video-library", "catalogue"),
        ("learning-platform", "learning"),
        ("agency-projects", "workspace"),
        ("clinic-bookings", "booking"),
        ("plant-shop", "storefront"),
        ("event-tickets", "booking"),
    ],
)
def test_the_requirements_words_pick_the_archetype(name, archetype):
    assert archetype_for((EXAMPLES / "requirements" / f"{name}.md").read_text()) == archetype


def test_without_words_the_product_type_then_a_back_office():
    assert archetype_for("Keep track of things.", ["Video Streaming/OTT"]) == "catalogue"
    assert archetype_for("Keep track of things.") == "back-office"


@pytest.mark.parametrize("archetype", sorted(ARCHETYPES))
def test_each_archetype_gives_its_frame(archetype):
    design, areas, replaced = complete_design({"archetype": archetype}, None, _backend("event-tickets"))
    defaults = ARCHETYPES[archetype]
    assert {k: design[k] for k in ("shell", "mobileNav", "frame")} == {
        k: defaults[k] for k in ("shell", "mobileNav", "frame")
    }
    assert "density" not in design, "the theme's density unless the brief sets one"
    assert areas == []


def test_a_view_that_does_not_fit_the_data_is_replaced_with_a_note():
    brief = {
        "archetype": "workspace",
        "mainEntity": "Task",
        "entities": [
            {"entity": "Task", "view": "board", "roles": {"title": "title", "badge": "priority", "stat": "title"}},
            {"entity": "Project", "view": "media-grid", "roles": {"title": "name"}},
            {"entity": "Ghost", "view": "table"},
        ],
    }
    design, _, replaced = complete_design(brief, None, _backend("agency-projects"))
    task, project = design["entities"]["Task"], design["entities"]["Project"]
    assert task["view"] == "board" and task["groupBy"] == "priority", "the badge names an enum: the board's columns"
    assert project["view"] == "cards"
    assert any("media grid needs an image" in line for line in replaced)
    assert any("'Ghost' is not in the BackendSpec" in line for line in replaced)
    assert any("stat 'title' left out (already the title)" in line for line in replaced)


def test_a_board_takes_the_status_flow_and_a_calendar_its_date():
    design, _, _ = complete_design(
        {"entities": {"Task": {"view": "board"}}, "mainEntity": "Task"}, None, _backend("agency-projects")
    )
    assert design["entities"]["Task"]["groupBy"] == "status", "the field with a transition rule"
    design, _, _ = complete_design(
        {"archetype": "booking", "mainEntity": "Appointment", "entities": {"Appointment": {"view": "calendar"}}},
        None,
        _backend("clinic-bookings"),
    )
    appointment = design["entities"]["Appointment"]
    assert appointment["view"] == "calendar" and appointment["dateField"] not in ("createdAt", "updatedAt")
    assert design["homeView"] == "agenda"


def test_geminis_shapes_are_read_as_written():
    """Story 23.0: entities as an object keyed by entity, `meta` as one string."""
    brief = json.loads(
        (Path(__file__).parent / "fixtures" / "app-golden" / "video-library" / "design-brief.json").read_text()
    )
    design, _, replaced = complete_design(brief, None, _backend("video-library"))
    video = design["entities"]["Video"]
    assert video["view"] == "media-grid" and video["roles"]["media"] == "thumbnail"
    assert video["roles"]["meta"] == ["publishDate"], "a string read as a list of one"
    assert any("subtitle 'category' left out (already the badge)" in line for line in replaced)
    assert design["homeView"] == "catalogue" and design["shell"] == "topbar"


def test_roles_must_fit_the_fields_type():
    brief = {"entities": {"Plant": {"view": "cards", "roles": {"media": "name", "price": "size", "title": "price"}}}}
    design, _, replaced = complete_design(brief, None, _backend("plant-shop"))
    roles = design["entities"]["Plant"]["roles"]
    assert "price" not in roles and roles.get("title") != "price"
    assert roles["media"] != "name", "the first image field instead"
    assert len([line for line in replaced if "left out" in line]) == 3


def test_filters_need_a_filter_the_list_has():
    brief = {"entities": {"Tag": {"view": "table", "filtersStyle": "chips"}}}
    design, _, replaced = complete_design(brief, None, _backend("news-feed"))
    assert design["entities"]["Tag"]["filtersStyle"] == "toolbar"
    assert any("chips need a filter" in line for line in replaced)


def test_looks_are_recipes_once_each():
    design, _, replaced = complete_design(
        {"looks": [{"recipe": "glass"}, "glass", {"recipe": "vaporwave"}, "brutalist"]}, None, _backend("news-feed")
    )
    assert [look["recipe"] for look in design["looks"]] == ["glass", "brutalist"]
    assert any("'vaporwave' is not a recipe" in line for line in replaced)


def test_areas_take_the_apps_roles_once_each():
    areas_raw = [
        {"id": "attendees", "label": "Attendees", "roles": ["attendee", "ghost"], "archetype": "catalogue",
         "shell": "topbar", "mainEntity": "Event", "entities": {"Event": {"view": "media-grid"}}},
        {"id": "Organizers", "roles": ["organizer", "attendee"], "archetype": "back-office", "mainEntity": "Event",
         "homeView": "dashboard", "entities": {"Event": {"view": "table"}}},
    ]  # fmt: skip
    design, areas, replaced = complete_design({"archetype": "catalogue"}, areas_raw, _backend("event-tickets"))
    assert [(a["id"], a["roles"], a["prefix"]) for a in areas] == [
        ("attendees", ["attendee"], "/"),
        ("organizers", ["organizer"], "/organizers"),
    ]
    assert areas[0]["design"]["shell"] == "topbar" and areas[1]["design"]["shell"] == "sidebar"
    assert areas[1]["design"]["entities"]["Event"]["view"] == "table"
    assert any("'ghost' is not a role of the app" in line for line in replaced)
    assert any("'attendee' is in another area" in line for line in replaced)


def test_one_area_is_the_app_itself():
    _, areas, replaced = complete_design(
        {}, [{"id": "all", "roles": ["attendee", "organizer"]}], _backend("event-tickets")
    )
    assert areas == [] and any("one area is the app itself" in line for line in replaced)


def test_an_outline_without_a_brief_keeps_its_own_choices():
    backend = _backend("flashcards")
    raw = json.loads((EXAMPLES / "app-outlines" / "flashcards.json").read_text())
    outline, notes = complete_outline(raw, backend, build_contract(backend, build_plan(backend)))
    design = outline["design"]
    assert (
        design["shell"] == "sidebar"
        and design["homeView"] == "dashboard"
        and outline["home"] == raw.get("home", "dashboard")
    )
    for name, entity in outline["entities"].items():
        if name in design["entities"] and raw.get("entities", {}).get(name, {}).get("listStyle"):
            assert design["entities"][name]["view"] == entity["listStyle"]


def test_a_brief_decides_the_home_page_and_the_spec_validates():
    backend = _backend("news-feed")
    raw = json.loads((EXAMPLES / "app-outlines" / "news-feed.json").read_text())
    raw["design"] = json.loads(
        (Path(__file__).parent / "fixtures" / "app-golden" / "news-feed" / "design-brief.json").read_text()
    )
    outline, notes = complete_outline(raw, backend, build_contract(backend, build_plan(backend)))
    assert outline["home"] == "Post" and outline["design"]["homeView"] == "feed"
    assert outline["design"]["entities"]["Post"]["view"] == "feed"
    backend, outline, _ = ensure_aggregates(backend, outline)
    contract = build_contract(backend, build_plan(backend))
    spec = app_frontend_spec(backend, outline, {"colorScheme": "light-dark"}, contract).spec
    result = validate_frontend_spec_data(spec)
    assert result.report.valid, result.report.errors
    data = app_data(plan_frontend(result.normalized, contract), result.normalized, contract)
    assert data["design"]["shell"] == "topbar" and data["design"]["entities"]["Post"]["view"] == "feed"
    assert data["areas"] == []


def test_the_kit_reads_todays_layout_for_an_app_drafted_before_epic_23():
    old = {"entities": {"Deck": {"listStyle": "cards"}}}
    assert kit_design(old) | {} == {
        "archetype": "back-office", "shell": "sidebar", "mobileNav": "drawer", "frame": "standard",
        "homeView": "dashboard", "entities": {}, "looks": [], "mainEntity": "Deck", "recipe": None,
    }  # fmt: skip


def test_the_v2_prompt_reads_the_outline_without_the_design():
    assert "design" not in outline_schema(design=False)["properties"]
    assert {"design", "areas"} <= set(outline_schema()["properties"])


def test_the_kit_has_every_shell():
    shell = (KIT / "AppShell.tsx").read_text()
    for marker in ("TopBarShell", "SidebarShell", "BottomTabs", 'design.shell !== "rail"', '"topbar-tabs"'):
        assert marker in shell
    assert "FRAME_WIDTH[layout.frame]" in (KIT / "AppPage.tsx").read_text()
