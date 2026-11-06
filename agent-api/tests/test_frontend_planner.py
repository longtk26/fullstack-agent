"""Frontend planner and theme tokens (Story 13.1)."""

import json
import os
from pathlib import Path

import pytest
from generation_helpers import EXAMPLES, PAIR_SPECS, app_pair

from src.modules.shared.domain.frontend_spec import validate_frontend_spec_text
from src.orchestrator.frontend.planner import (
    dump_frontend_plan,
    operation_function,
    plan_frontend,
    primitive_closure,
    route_file,
)
from src.orchestrator.frontend.theme import build_theme, contrast, globals_css

SNAPSHOTS = Path(__file__).parent / "fixtures" / "frontend-plans"
# Static sites plan here; dynamic apps plan in `frontend/app/` (tests/test_app_screens.py, Story 22.8).
STATIC = {
    "static-landing": EXAMPLES / "frontend-specs",
    "shop-static": Path(__file__).parent / "fixtures" / "frontend-specs",
}


def frontend(name: str) -> dict:
    result = validate_frontend_spec_text((STATIC[name] / f"{name}.json").read_text())
    assert result.report.valid, result.report.errors
    return result.normalized


def plan(name: str) -> dict:
    return plan_frontend(frontend(name))


@pytest.mark.parametrize("name", ["static-landing"])
def test_plan_matches_snapshot(name):
    text = dump_frontend_plan(plan(name))
    assert text == dump_frontend_plan(plan(name))
    snapshot = SNAPSHOTS / f"{name}.plan.json"
    if os.environ.get("UPDATE_SNAPSHOTS") or not snapshot.exists():
        snapshot.parent.mkdir(exist_ok=True)
        snapshot.write_text(text)
    assert text == snapshot.read_text(), "frontend plan changed: review, then rerun with UPDATE_SNAPSHOTS=1"


def test_dynamic_frontends_need_the_contract():
    app = validate_frontend_spec_text(json.dumps(app_pair("shop")[0])).normalized
    with pytest.raises(ValueError, match="against the API contract"):
        plan_frontend(app, None)


def test_routes_and_names_follow_the_app_router_and_the_skill():
    assert route_file("/") == "src/app/page.tsx"
    assert route_file("/products/[id]") == "src/app/products/[id]/page.tsx"
    assert operation_function("product.list", "list") == "listProducts"
    assert operation_function("cartItem.create", "create") == "createCartItem"
    assert operation_function("order.checkout", None) == "checkoutOrder"


def test_shadcn_list_includes_what_the_primitives_import():
    shop = plan("shop-static")  # its custom components use card, badge, pagination, skeleton, separator, item
    assert {"card", "badge", "pagination", "skeleton", "separator", "item"} <= set(shop["shadcn"])
    assert "button" in primitive_closure({"pagination"})  # pagination imports button
    assert set(primitive_closure({"sidebar"})) >= {"sheet", "tooltip", "input", "separator", "skeleton"}


def test_theme_tokens_keep_text_readable_in_both_schemes():
    shop = build_theme(json.loads((PAIR_SPECS / "shop.json").read_text())["theme"])
    for palette in (shop["light"], shop["dark"]):
        assert contrast(palette["foreground"], palette["background"]) >= 4.5
        assert contrast(palette["primary-foreground"], palette["primary"]) >= 4.5
        assert contrast(palette["muted-foreground"], palette["background"]) >= 3
    assert shop["light"]["primary"] == "#1d4ed8" and shop["radius"] == "0.625rem"
    landing = plan("static-landing")["theme"]
    assert landing["dark"] is None and landing["fonts"]["heading"].startswith('"Playfair Display", ui-serif')
    css = globals_css(shop)
    assert ".dark {" in css and "--primary: #1d4ed8;" in css and "--radius: 0.625rem;" in css


def test_dark_only_schemes_put_the_dark_palette_in_root():
    theme = build_theme({**frontend("static-landing")["theme"], "colorScheme": "dark"})
    assert theme["light"]["background"] == theme["dark"]["background"]
    assert (json.loads(json.dumps(theme))["light"]["foreground"]).startswith("#")
