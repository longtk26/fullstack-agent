"""Style recipes and the three looks (Epic 23, Story 23.7). A recipe is a set of tokens and CSS in the app kit
(`globals.css` from `templates/nextjs_overlay/files/dynamic/app/src/app/recipes.css`); the brief names three looks and
code completes them: the requirement's own style words come first, the product's styles from UI UX Pro Max's data
fill gaps, guards keep unsuitable recipes away from sensitive products, and the three span a range (Story 23.0: the
model alone picked only quiet looks in all seven drafts).

Pure functions, no model call.
"""

import re
from functools import cache
from pathlib import Path
from typing import Any

RECIPES_CSS = Path(__file__).with_name("recipes.css")
_BLOCK = re.compile(r"/\* recipe: ([a-z]+) \*/\n(.*?)/\* end \*/", re.S)

RECIPES = (
    "minimal", "swiss", "material", "enterprise", "soft", "clay",
    "glass", "aurora", "brutalist", "neon", "playful", "editorial",
)  # fmt: skip
# How loud a recipe is: the three looks span at least two families, one of them not quiet.
FAMILIES = {
    "quiet": ("minimal", "swiss", "enterprise", "editorial", "material"),
    "soft": ("soft", "clay", "playful"),
    "bold": ("glass", "aurora", "brutalist", "neon"),
}
FAMILY = {recipe: family for family, recipes in FAMILIES.items() for recipe in recipes}
# UI UX Pro Max's style names (products.csv "Primary Style Recommendation", "Secondary Styles") → a recipe.
STYLE_RECIPES: tuple[tuple[str, str], ...] = (
    ("liquid glass", "glass"),
    ("glassmorphism", "glass"),
    ("neumorphism", "soft"),
    ("soft ui", "soft"),
    ("claymorphism", "clay"),
    ("aurora", "aurora"),
    ("gradient", "aurora"),
    ("neubrutalism", "brutalist"),
    ("brutalism", "brutalist"),
    ("cyberpunk", "neon"),
    ("neon", "neon"),
    ("dark mode", "neon"),
    ("y2k", "playful"),
    ("frutiger", "playful"),
    ("vibrant", "playful"),
    ("playful", "playful"),
    ("swiss", "swiss"),
    ("material", "material"),
    ("editorial", "editorial"),
    ("magazine", "editorial"),
    ("corporate", "enterprise"),
    ("enterprise", "enterprise"),
    ("data-dense", "enterprise"),
    ("trust", "enterprise"),
    ("minimalism", "minimal"),
    ("flat design", "minimal"),
    ("minimal", "minimal"),
)
# Words in a requirement that ask for a look (whole words or phrases).
STYLE_WORDS: tuple[tuple[str, str], ...] = (
    ("liquid glass", "glass"),
    ("glassmorphism", "glass"),
    ("glass", "glass"),
    ("frosted", "glass"),
    ("neumorphism", "soft"),
    ("neumorphic", "soft"),
    ("claymorphism", "clay"),
    ("aurora", "aurora"),
    ("gradients", "aurora"),
    ("neo-brutalism", "brutalist"),
    ("neobrutalism", "brutalist"),
    ("brutalist", "brutalist"),
    ("brutalism", "brutalist"),
    ("cyberpunk", "neon"),
    ("neon", "neon"),
    ("y2k", "playful"),
    ("frutiger aero", "playful"),
    ("playful", "playful"),
    ("swiss", "swiss"),
    ("material design", "material"),
    ("editorial", "editorial"),
    ("magazine", "editorial"),
    ("minimalist", "minimal"),
    ("minimal", "minimal"),
)
# Products whose users expect calm: no dark neon or toy look (styles.csv "Do Not Use For", in short).
SENSITIVE = ("health", "medical", "clinic", "dental", "dentist", "hospital", "patient", "pharmacy", "therapy",
             "bank", "banking", "finance", "financial", "accounting", "insurance", "legal", "law", "tax")  # fmt: skip
GUARDED = {"neon": "a dark neon look", "playful": "a toy-like look"}
DEFAULT_BOLD = ("aurora", "glass", "brutalist")


def _words(text: str) -> str:
    return " " + re.sub(r"[^a-z0-9-]+", " ", text.lower()) + " "


def style_words(requirement: str) -> list[str]:
    """The looks a requirement asks for in its own words, in the order it names them."""
    text = _words(requirement)
    found: list[tuple[int, str]] = []
    for phrase, recipe in STYLE_WORDS:
        index = text.find(f" {phrase} ")
        if index >= 0 and all(recipe != r for _, r in found):
            found.append((index, recipe))
    return [recipe for _, recipe in sorted(found)]


def recipe_for(style: str) -> str | None:
    lower = style.lower()
    return next((recipe for name, recipe in STYLE_RECIPES if name in lower), None)


def recommended_looks(product_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """The recipes UI UX Pro Max's data names for the ranked product types (primary styles first), with why."""
    out: list[dict[str, str]] = []
    for row in product_rows:
        product = row.get("Product Type", "")
        styles = [
            *re.split(r"\s*\+\s*", row.get("Primary Style Recommendation", "")),
            *re.split(r"\s*,\s*", row.get("Secondary Styles", "")),
        ]
        for style in styles:
            recipe = recipe_for(style)
            if recipe and all(recipe != item["recipe"] for item in out):
                out.append({"recipe": recipe, "why": f"{style.strip()} for {product}"})
    return out[:5]


def sensitive(requirement: str, product_types: list[str]) -> bool:
    text = _words(requirement + " " + " ".join(product_types))
    return any(f" {word} " in text for word in SENSITIVE)


def complete_looks(
    looks: list[dict[str, Any]], requirement: str, recommended: list[dict[str, str]], product_types: list[str]
) -> tuple[list[dict[str, Any]], list[str]]:
    """Three looks: the requirement's style words first, then the brief's, then the data's; guarded recipes left out
    for sensitive products; the three span a range (not all quiet). Returns the looks and what code changed."""
    notes: list[str] = []
    calm = sensitive(requirement, product_types)
    candidates: list[dict[str, Any]] = []
    for recipe in style_words(requirement):
        candidates.append({"recipe": recipe, "reason": "The requirement asks for it"})
    candidates += [look for look in looks if isinstance(look, dict) and look.get("recipe") in RECIPES]
    candidates += [{"recipe": item["recipe"], "reason": f"Recommended: {item['why']}"} for item in recommended]
    out: list[dict[str, Any]] = []
    for look in candidates:
        recipe = look["recipe"]
        if any(recipe == kept["recipe"] for kept in out):
            continue
        if calm and recipe in GUARDED and recipe not in style_words(requirement):
            notes.append(f"look '{recipe}' left out: {GUARDED[recipe]} does not suit this product")
            continue
        out.append({"recipe": recipe, **({"reason": str(look["reason"])[:200]} if look.get("reason") else {})})
    for recipe in ("minimal", *DEFAULT_BOLD):
        if len(out) >= 3:
            break
        if all(recipe != kept["recipe"] for kept in out):
            out.append({"recipe": recipe, "reason": "Added by code"})
            notes.append(f"look '{recipe}' added by code (fewer than three)")
    out = out[:3]
    if all(FAMILY[look["recipe"]] == "quiet" for look in out):
        bold = next(
            (item["recipe"] for item in recommended if FAMILY.get(item["recipe"]) != "quiet"
             and not (calm and item["recipe"] in GUARDED)),
            next(r for r in ("soft", *DEFAULT_BOLD) if not (calm and r in GUARDED)),
        )  # fmt: skip
        if all(bold != kept["recipe"] for kept in out):
            notes.append(f"look '{out[2]['recipe']}' replaced by '{bold}': three quiet looks offer no choice")
            out[2] = {"recipe": bold, "reason": "A bolder option (added by code)"}
    return out, notes


def first_recipe(design: dict[str, Any]) -> str:
    """The look on screen: the user's pick (`design.recipe`), else the first look, else minimal."""
    return design.get("recipe") or next((look["recipe"] for look in design.get("looks") or []), "minimal")


@cache
def recipe_blocks() -> dict[str, str]:
    """Each recipe's CSS (`recipes.css`), placeholders still in."""
    return {name: body for name, body in _BLOCK.findall(RECIPES_CSS.read_text())}


def recipe_css(recipe: str | None) -> str:
    """The app's recipe, ready to append to `globals.css`: `@root` → `:root` (later than the theme's, so it wins),
    `@dark` → `:root.dark`; empty for no recipe (an app drafted before Epic 23 keeps today's look)."""
    body = recipe_blocks().get(recipe or "")
    if body is None:
        return ""
    css = body.replace("@dark", ":root.dark").replace("@root", ":root")
    return (
        f"\n/* Style recipe: {recipe} (Epic 23, Story 23.7) */\n{css}"
        "@media (prefers-reduced-motion: reduce) {\n  :root * { transition: none !important; }\n}\n"
    )
