"""The requirement's own look comes before the design data's (2026-11-07): a drafted volunteer app asked for "warm"
and got the blue of the product type the data matched; a pet adoption app asks for "photo-first … a bright orange
accent on white". The draft writes what the requirement says as values (`design.requested`), code applies them."""

import json
from pathlib import Path

from src.modules.shared.domain.backend_spec import validate_spec_data
from src.orchestrator.frontend.app.design import complete_design
from src.orchestrator.frontend.app.requested import follow_requested
from src.orchestrator.frontend.theme import contrast, on

EXAMPLES = Path(__file__).parents[2] / "examples"
BLUE = {"primary": "#2563eb", "secondary": "#f1f5fd", "accent": "#059669", "background": "#ffffff",
        "foreground": "#0f172a", "muted": "#f1f5fd", "destructive": "#dc2626"}  # fmt: skip


def _theme() -> dict:
    typography = {"headingFont": "DM Sans", "bodyFont": "DM Sans"}
    return {"style": "minimal", "colorScheme": "light-dark", "colors": dict(BLUE), "typography": typography,
            "radius": "sm", "density": "comfortable"}  # fmt: skip


def _plants(requested: dict) -> dict:
    backend = validate_spec_data(json.loads((EXAMPLES / "specs" / "plant-shop.json").read_text())).normalized
    brief = {"mainEntity": "Plant", "entities": {"Plant": {"view": "cards"}, "Order": {"view": "table"}},
             "requested": requested}  # fmt: skip
    design, areas, _ = complete_design(brief, None, backend)
    return {"design": design, "areas": areas}


def test_a_photo_first_orange_on_white_app():
    outline = _plants({"accent": "#F97316", "background": "#ffffff", "photos": "prominent", "corners": "rounded",
                       "words": "photo-first, a bright orange accent on white"})  # fmt: skip
    theme = _theme()
    notes = follow_requested(outline, theme)
    colors = theme["colors"]
    assert colors["primary"] != BLUE["primary"] and colors["primary"].startswith("#")
    red, green, blue = (int(colors["primary"][i : i + 2], 16) for i in (1, 3, 5))
    assert red > green > blue, "still orange, only darker if the white text needed it"
    assert contrast(on(colors["primary"]), colors["primary"]) >= 4.5
    assert colors["background"] == "#ffffff" and theme["radius"] == "lg"
    plant, order = outline["design"]["entities"]["Plant"], outline["design"]["entities"]["Order"]
    assert plant["view"] == "media-grid" and plant["detailView"] == "media"
    assert order["view"] == "table" and order.get("detailView") in (None, "record"), "no image: unchanged"
    assert len(notes) == 1 and "follows the requirement (photo-first" in notes[0]["message"]
    assert "photos first (Plant)" in notes[0]["message"]


def test_a_cream_and_brown_app_with_serif_headings():
    outline = _plants({"background": "#f5efe6", "text": "#3e2723", "headingFont": "serif"})
    theme = _theme()
    follow_requested(outline, theme)
    colors = theme["colors"]
    assert colors["background"] == "#f5efe6" and colors["foreground"] == "#3e2723"
    assert colors["muted"] != BLUE["muted"], "the surfaces follow the cream, not the old blue tint"
    assert theme["typography"] == {"headingFont": "Lora", "bodyFont": "DM Sans"}


def test_a_dark_theme_with_a_loud_accent():
    outline = _plants({"scheme": "dark", "accent": "#d946ef", "headingFont": "sans"})
    theme = _theme()
    follow_requested(outline, theme)
    assert theme["colorScheme"] == "dark" and theme["typography"]["headingFont"] == "DM Sans", "a sans already"


def test_nothing_requested_changes_nothing():
    outline = _plants({})
    theme = _theme()
    assert follow_requested(outline, theme) == [] and theme == _theme()
    assert outline["design"]["entities"]["Plant"]["view"] == "cards"


def test_values_that_do_not_fit_are_left_out_with_a_note():
    backend = validate_spec_data(json.loads((EXAMPLES / "specs" / "plant-shop.json").read_text())).normalized
    brief = {"requested": {"accent": "orange", "scheme": "dark", "corners": "soft"}}
    design, _, replaced = complete_design(brief, None, backend)
    assert design["requested"] == {"scheme": "dark"}
    assert any("requested accent 'orange'" in line for line in replaced)
    assert any("requested corners 'soft'" in line for line in replaced)
