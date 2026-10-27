"""Frontend planner and theme tokens (Story 13.1)."""

import json
import os
from pathlib import Path

import pytest
from generation_helpers import EXAMPLES, normalized

from src.modules.shared.domain.frontend_spec import validate_frontend_spec_text
from src.orchestrator.contract import build_contract
from src.orchestrator.frontend_planner import (
    dump_frontend_plan,
    operation_function,
    plan_frontend,
    primitive_closure,
    route_file,
)
from src.orchestrator.frontend_theme import build_theme, contrast, globals_css

SNAPSHOTS = Path(__file__).parent / "fixtures" / "frontend-plans"
PAIRS = {"static-landing": None, "shop-dynamic": "shop", "project-tracker-dynamic": "two-entity"}


def frontend(name: str) -> dict:
    result = validate_frontend_spec_text((EXAMPLES / "frontend-specs" / f"{name}.json").read_text())
    assert result.report.valid, result.report.errors
    return result.normalized


def plan(name: str) -> dict:
    backend = PAIRS[name]
    contract = build_contract(normalized(EXAMPLES / "specs" / f"{backend}.json")) if backend else None
    return plan_frontend(frontend(name), contract)


@pytest.mark.parametrize("name", PAIRS)
def test_plan_matches_snapshot(name):
    text = dump_frontend_plan(plan(name))
    assert text == dump_frontend_plan(plan(name))
    snapshot = SNAPSHOTS / f"{name}.plan.json"
    if os.environ.get("UPDATE_SNAPSHOTS") or not snapshot.exists():
        snapshot.parent.mkdir(exist_ok=True)
        snapshot.write_text(text)
    assert text == snapshot.read_text(), "frontend plan changed: review, then rerun with UPDATE_SNAPSHOTS=1"


def test_dynamic_frontends_need_the_contract():
    with pytest.raises(ValueError):
        plan_frontend(frontend("shop-dynamic"), None)


def test_routes_and_names_follow_the_app_router_and_the_skill():
    assert route_file("/") == "src/app/page.tsx"
    assert route_file("/products/[id]") == "src/app/products/[id]/page.tsx"
    assert operation_function("product.list", "list") == "listProducts"
    assert operation_function("cartItem.create", "create") == "createCartItem"
    assert operation_function("order.checkout", None) == "checkoutOrder"


def test_shop_plan_routes_components_bindings_forms_and_tests():
    shop = plan("shop-dynamic")
    assert [route["route"] for route in shop["routes"]] == [
        "/", "/products", "/products/[id]", "/cart", "/contact", "/about",
    ]  # fmt: skip
    components = {component["name"]: component for component in shop["components"]}
    assert components["ProductGrid"]["file"] == "src/features/products/components/ProductGrid.tsx"
    assert components["ProductGrid"]["hook"] == {
        "name": "useProductGrid",
        "file": "src/features/products/hooks/use-product-grid.ts",
    }
    assert components["Hero"]["file"] == "src/components/sections/Hero.tsx" and "hook" not in components["Hero"]
    assert components["Form"]["usedBy"] == ["product-detail", "contact"]
    binding = next(b for b in shop["data"] if b["section"] == "detail")
    assert binding["hook"] == "useGetProduct" and binding["params"] == {"id": "$route.id"}
    assert binding["queryKey"] == "productKeys.detail(params)"
    add_to_cart = next(form for form in shop["forms"] if form["id"] == "addToCart")
    assert add_to_cart["schema"] == "addToCartSchema" and add_to_cart["valuesType"] == "TAddToCartValues"
    assert add_to_cart["hook"] == "useCreateCartItem" and add_to_cart["requestFields"] == ["productId", "quantity"]
    tests = {test["id"]: test for test in shop["tests"]}
    assert tests["route:product-detail"]["path"] == "/products/8d2e7a40-1f3b-4c55-8e6a-2b9f4c3d0001"
    assert tests["form:contact"]["path"] == "/contact"


def test_shadcn_list_includes_what_the_primitives_import():
    shop = plan("shop-dynamic")
    assert {"card", "badge", "pagination", "field", "input", "textarea", "sonner"} <= set(shop["shadcn"])
    assert "button" in primitive_closure({"pagination"})  # pagination imports button
    assert set(primitive_closure({"sidebar"})) >= {"sheet", "tooltip", "input", "separator", "skeleton"}


def test_theme_tokens_keep_text_readable_in_both_schemes():
    shop = plan("shop-dynamic")["theme"]
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
