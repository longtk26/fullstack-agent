"""Fonts that load (Story 17.7): the curated set bundled with the pinned frontend base as `@fontsource` packages.

A theme font in this set is imported from its package (`src/app/fonts.ts`), so it installs offline from the
pre-warmed pnpm store and ships with the static export; any other name is only written into the CSS font stack and
shows as the fallback on machines without it, so the validator suggests the closest bundled font. The set comes from
the pairings in UI UX Pro Max's `typography.csv` (docs/research/design-skills.md): its most used families, the theme
presets' fonts, and two monospace fonts. Adding a font: add it here, then `make frontend-base` and `make runner-node`.
"""

import difflib
from dataclasses import dataclass
from typing import Literal

FontCategory = Literal["sans", "serif", "display", "mono"]
LOADED_WEIGHTS = (400, 500, 600, 700)  # body, medium, semibold, bold: what the section library uses


@dataclass(frozen=True)
class Font:
    name: str
    category: FontCategory
    weights: tuple[int, ...] = LOADED_WEIGHTS

    @property
    def package(self) -> str:
        return "@fontsource/" + self.name.lower().replace(" ", "-")


FONTS: dict[str, Font] = {
    font.name: font
    for font in (
        Font("Inter", "sans"),
        Font("Space Grotesk", "sans"),
        Font("Plus Jakarta Sans", "sans"),
        Font("DM Sans", "sans"),
        Font("Outfit", "sans"),
        Font("IBM Plex Sans", "sans"),
        Font("Poppins", "sans"),
        Font("Rubik", "sans"),
        Font("Nunito", "sans"),
        Font("Source Sans 3", "sans"),
        Font("Roboto", "sans"),
        Font("Montserrat", "sans"),
        Font("Atkinson Hyperlegible", "sans", (400, 700)),
        Font("Playfair Display", "display"),
        Font("Cormorant Garamond", "display"),
        Font("EB Garamond", "serif"),
        Font("Crimson Pro", "serif"),
        Font("Source Serif 4", "serif"),
        Font("Lora", "serif"),
        Font("Merriweather", "serif"),
        Font("JetBrains Mono", "mono"),
        Font("Space Mono", "mono", (400, 700)),
    )
}
_DEFAULT_BY_CATEGORY: dict[FontCategory, str] = {
    "sans": "Inter",
    "serif": "Source Serif 4",
    "display": "Playfair Display",
    "mono": "JetBrains Mono",
}
_SERIF_HINTS = ("serif", "garamond", "baskerville", "caslon", "didot", "bodoni", "times", "georgia", "slab")
_DISPLAY_HINTS = ("display", "playfair", "abril", "fatface", "cormorant")
_MONO_HINTS = ("mono", "code", "courier")


def bundled_font(name: str) -> Font | None:
    return FONTS.get(name)


def guess_category(name: str) -> FontCategory:
    """The kind of an unknown family, from its name ("Fira Code" → mono, "Libre Baskerville" → serif)."""
    lowered = name.lower()
    if any(hint in lowered for hint in _MONO_HINTS):
        return "mono"
    if any(hint in lowered for hint in _DISPLAY_HINTS):
        return "display"
    if "sans" not in lowered and any(hint in lowered for hint in _SERIF_HINTS):
        return "serif"
    return "sans"


def font_category(name: str) -> FontCategory:
    font = FONTS.get(name)
    return font.category if font else guess_category(name)


def closest_font(name: str) -> str:
    """The bundled font to suggest for `name`: a near spelling ("Playfair" → Playfair Display, "inter" → Inter),
    else the default of its kind."""
    by_lower = {font.lower(): font for font in FONTS}
    if name.lower() in by_lower:
        return by_lower[name.lower()]
    category = guess_category(name)
    same_kind = [font.name for font in FONTS.values() if font.category == category]
    lowered = name.lower()
    prefixed = [font for font in same_kind if font.lower().startswith(lowered) or lowered.startswith(font.lower())]
    if prefixed:
        return prefixed[0]
    close = difflib.get_close_matches(lowered, [font.lower() for font in same_kind], n=1, cutoff=0.75)
    return by_lower[close[0]] if close else _DEFAULT_BY_CATEGORY[category]


def font_imports(*names: str) -> list[str]:
    """CSS files to import for these theme fonts (bundled ones only; each family once)."""
    imports: list[str] = []
    for name in dict.fromkeys(names):
        font = FONTS.get(name)
        if font is not None:
            imports += [f"{font.package}/{weight}.css" for weight in font.weights]
    return imports
