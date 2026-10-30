"""Design tokens for a generated frontend (Story 13.1): FrontendSpec theme → shadcn CSS variables, light and dark.

The spec names a handful of brand colours; every other token (foregrounds, card, border, ring, charts, sidebar)
is derived so text keeps its contrast. Hex colours are mixed in sRGB; other CSS colour syntaxes are passed through
and their derived tokens fall back to the theme preset. Deterministic: same theme, same tokens.
"""

import re
from typing import Any

from src.modules.shared.domain.frontend_spec import THEME_PRESETS, font_category, font_imports

_HEX = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})([0-9a-fA-F]{2})?$")
RADIUS = {"none": "0rem", "sm": "0.375rem", "md": "0.625rem", "lg": "0.875rem", "full": "1.25rem"}
FONT_FALLBACK = 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif'
SERIF_FALLBACK = 'ui-serif, Georgia, "Times New Roman", serif'
MONO_FALLBACK = 'ui-monospace, "SF Mono", Menlo, Consolas, monospace'
LIGHT_TEXT, DARK_TEXT = "#ffffff", "#0a0a0a"
# Dark mode never uses pure black or white (design checklist, Story 17.7).
OFF_BLACK, OFF_WHITE = "#0a0a0a", "#fafafa"


def _rgb(color: str) -> tuple[float, float, float] | None:
    match = _HEX.match(color)
    if not match:
        return None
    digits = match.group(1)
    if len(digits) == 3:
        digits = "".join(ch * 2 for ch in digits)
    return tuple(int(digits[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def _hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{round(max(0.0, min(1.0, c)) * 255):02x}" for c in rgb)


def mix(first: str, second: str, amount: float) -> str | None:
    """`amount` of `second` mixed into `first` (0 → first, 1 → second); None unless both are hex."""
    a, b = _rgb(first), _rgb(second)
    if a is None or b is None:
        return None
    return _hex(tuple(x + (y - x) * amount for x, y in zip(a, b, strict=True)))  # type: ignore[arg-type]


def luminance(color: str) -> float | None:
    rgb = _rgb(color)
    if rgb is None:
        return None
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(first: str, second: str) -> float | None:
    a, b = luminance(first), luminance(second)
    if a is None or b is None:
        return None
    lighter, darker = max(a, b), min(a, b)
    return (lighter + 0.05) / (darker + 0.05)


def on(color: str) -> str:
    """Text colour for a background: white or near-black, whichever contrasts more."""
    light, dark = contrast(color, LIGHT_TEXT), contrast(color, DARK_TEXT)
    if light is None or dark is None:
        return LIGHT_TEXT
    return LIGHT_TEXT if light >= dark else DARK_TEXT


def _readable(color: str, background: str, minimum: float = 3.0) -> str:
    """Lightens or darkens `color` toward the background's opposite until it reaches `minimum` contrast."""
    target = LIGHT_TEXT if (luminance(background) or 0) < 0.5 else DARK_TEXT
    current = color
    for step in range(1, 11):
        ratio = contrast(current, background)
        if ratio is None or ratio >= minimum:
            return current
        current = mix(color, target, step / 10) or color
    return current


def _palette(colors: dict[str, str], fallback: dict[str, str], dark: bool) -> dict[str, str]:
    background, foreground = colors["background"], colors["foreground"]
    if dark:
        if (luminance(background) or 1) > 0.5:
            background, foreground = mix(foreground, "#000000", 0.35) or fallback["foreground"], background
        if luminance(background) is None:
            background, foreground = OFF_BLACK, OFF_WHITE
        if (luminance(background) or 0) < (luminance(OFF_BLACK) or 0):
            background = OFF_BLACK
        if (luminance(foreground) or 0) > (luminance(OFF_WHITE) or 0):
            foreground = OFF_WHITE

    def derive(value: str | None, key: str) -> str:
        return value if value is not None else fallback[key]

    primary = colors["primary"]
    accent_base = colors["accent"]
    secondary = colors["secondary"]
    muted = colors["muted"]
    if dark:
        primary = _readable(primary, background)
        accent_base = _readable(accent_base, background)
        secondary = derive(mix(background, foreground, 0.12), "secondary")
        muted = derive(mix(background, foreground, 0.1), "muted")
    card = derive(mix(background, foreground, 0.04 if dark else 0.0), "background")
    border = derive(mix(background, foreground, 0.16 if dark else 0.12), "muted")
    palette = {
        "background": background,
        "foreground": foreground,
        "card": card,
        "card-foreground": foreground,
        "popover": card,
        "popover-foreground": foreground,
        "primary": primary,
        "primary-foreground": on(primary),
        "secondary": secondary,
        "secondary-foreground": derive(foreground if _rgb(secondary) else None, "foreground"),
        "muted": muted,
        "muted-foreground": derive(mix(foreground, background, 0.42), "foreground"),
        "accent": derive(mix(background, accent_base, 0.18 if dark else 0.12), "muted"),
        "accent-foreground": foreground,
        "destructive": _readable(colors["destructive"], background) if dark else colors["destructive"],
        "border": border,
        "input": border,
        "ring": primary,
        "chart-1": primary,
        "chart-2": accent_base,
        "chart-3": derive(mix(primary, foreground, 0.4), "primary"),
        "chart-4": derive(mix(accent_base, background, 0.35), "accent"),
        "chart-5": derive(mix(primary, background, 0.5), "primary"),
        "sidebar": derive(mix(background, foreground, 0.03), "background"),
        "sidebar-foreground": foreground,
        "sidebar-primary": primary,
        "sidebar-primary-foreground": on(primary),
        "sidebar-accent": derive(mix(background, foreground, 0.08), "muted"),
        "sidebar-accent-foreground": foreground,
        "sidebar-border": border,
        "sidebar-ring": primary,
    }
    return palette


def font_stack(name: str) -> str:
    category = font_category(name)
    fallback = {"serif": SERIF_FALLBACK, "display": SERIF_FALLBACK, "mono": MONO_FALLBACK}.get(category, FONT_FALLBACK)
    return f'"{name}", {fallback}'


def inverse_palette(palette: dict[str, str]) -> dict[str, str]:
    """Tokens inside a section on the primary colour (`background: "primary"`): the page's primary becomes the
    background and its foreground the text, so cards, muted text and buttons inside keep their contrast."""
    base, text = palette["primary"], palette["primary-foreground"]

    def tint(amount: float) -> str:
        return mix(base, text, amount) or f"color-mix(in oklab, {base} {100 - round(amount * 100)}%, {text})"

    return {
        "background": base,
        "foreground": text,
        "card": tint(0.08),
        "card-foreground": text,
        "popover": tint(0.08),
        "popover-foreground": text,
        "primary": text,
        "primary-foreground": base,
        "secondary": tint(0.14),
        "secondary-foreground": text,
        "muted": tint(0.12),
        "muted-foreground": tint(0.78),
        "accent": tint(0.16),
        "accent-foreground": text,
        "border": tint(0.24),
        "input": tint(0.24),
        "ring": text,
    }


def build_theme(theme: dict[str, Any]) -> dict[str, Any]:
    """`theme` is the normalized FrontendSpec theme (every colour filled from its preset)."""
    preset = THEME_PRESETS[theme["style"]]
    colors = {key: theme["colors"].get(key) or preset["colors"][key] for key in preset["colors"]}
    fallback = {**preset["colors"]}
    scheme = theme["colorScheme"]
    light = _palette(colors, fallback, dark=False)
    dark = _palette(colors, fallback, dark=True)
    typography = theme["typography"]
    return {
        "colorScheme": scheme,
        "light": dark if scheme == "dark" else light,
        "dark": dark if scheme != "light" else None,
        "radius": RADIUS[theme["radius"]],
        "density": theme["density"],
        "fonts": {
            "heading": font_stack(typography["headingFont"]),
            "body": font_stack(typography["bodyFont"]),
            "imports": font_imports(typography["headingFont"], typography["bodyFont"]),
        },
        "scale": typography.get("scale", "default"),
    }


def globals_css(theme: dict[str, Any]) -> str:
    """`src/app/globals.css`: the only place colours are written (nextjs-skills design-token rule)."""

    def block(selector: str, palette: dict[str, str], extra: list[str]) -> str:
        lines = [f"  --{name}: {value};" for name, value in palette.items()] + extra
        return f"{selector} {{\n" + "\n".join(lines) + "\n}\n"

    scale = {"compact": "15px", "default": "16px", "large": "17px"}[theme["scale"]]
    root_extra = [
        f"  --radius: {theme['radius']};",
        f"  --font-body: {theme['fonts']['body']};",
        f"  --font-display: {theme['fonts']['heading']};",
        f"  --density-gap: {'0.75rem' if theme['density'] == 'compact' else '1.25rem'};",
    ]
    parts = [
        "/* Generated from the FrontendSpec theme by the Fullstack Generation Agent. Do not edit:\n"
        "   change the theme in the FrontendSpec and regenerate. Components use the tokens, never raw colours. */\n",
        '@import "tailwindcss";\n@import "tw-animate-css";\n@import "shadcn/tailwind.css";\n',
        "@custom-variant dark (&:is(.dark *));\n",
        "@theme inline {\n"
        + "\n".join(f"  --color-{name}: var(--{name});" for name in theme["light"])
        + "\n  --font-sans: var(--font-body);\n  --font-heading: var(--font-display);\n"
        "  --radius-sm: calc(var(--radius) * 0.6);\n  --radius-md: calc(var(--radius) * 0.8);\n"
        "  --radius-lg: var(--radius);\n  --radius-xl: calc(var(--radius) * 1.4);\n"
        "  --radius-2xl: calc(var(--radius) * 1.8);\n  --spacing-section: var(--density-gap);\n}\n",
        block(":root", theme["light"], root_extra),
    ]
    if theme["dark"] is not None and theme["colorScheme"] == "light-dark":
        parts.append(block(".dark", theme["dark"], []))
    parts.append(block(".surface-inverse", inverse_palette(theme["light"]), []))
    if theme["dark"] is not None and theme["colorScheme"] == "light-dark":
        parts.append(block(".dark .surface-inverse", inverse_palette(theme["dark"]), []))
    parts.append(
        "@layer base {\n  * {\n    @apply border-border outline-ring/50;\n  }\n"
        f"  html {{\n    @apply font-sans;\n    font-size: {scale};\n  }}\n"
        "  body {\n    @apply bg-background text-foreground;\n  }\n"
        "  h1, h2, h3, h4 {\n    font-family: var(--font-display);\n  }\n}\n"
    )
    return "\n".join(parts)


def fonts_ts(theme: dict[str, Any]) -> str:
    """`src/app/fonts.ts`: the theme's bundled fonts (Story 17.7), imported by the root layout. Next.js copies the
    font files into the build, so they load offline and in the static export."""
    imports = "".join(f'import "{path}";\n' for path in theme["fonts"].get("imports", []))
    note = "" if imports else "// The theme's fonts are not in the bundled set; the CSS font stack names them.\n"
    return (
        "// Generated from the FrontendSpec theme by the Fullstack Generation Agent. Do not edit.\n"
        + note
        + imports
        + "\nexport {};\n"
    )
