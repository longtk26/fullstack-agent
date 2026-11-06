"""Japanese and English typesetting for apps (Epic 23, Story 23.8). A Japanese app gets a bundled Japanese face after
its Latin one (so Latin words keep the theme's face and kana and kanji never fall back to the device's font), and
`:lang(ja)` rules suited to Japanese: a looser line height, no uppercase or wide tracking, capped heading weight,
proportional punctuation on headings and phrase-aware line breaks. App-only: static sites keep their own path (20.10).
"""

import re
from typing import Any

from src.modules.shared.domain.frontend_spec.fonts import FONTS, JA_FALLBACK, JA_FONTS, JA_SERIF_FALLBACK

# A look's Japanese face (Story 23.8): mincho for editorial looks, a UD gothic for dense business screens, a rounded
# face for soft and playful ones, a crisp gothic for quiet ones; Noto Sans JP otherwise.
JA_FACE = {
    "editorial": "Shippori Mincho",
    "enterprise": "BIZ UDPGothic",
    "clay": "M PLUS 1p",
    "playful": "M PLUS 1p",
    "soft": "M PLUS 1p",
    "minimal": "Zen Kaku Gothic New",
    "swiss": "Zen Kaku Gothic New",
}
DEFAULT_JA_FACE = "Noto Sans JP"
_KANA = re.compile(r"[぀-ヿ]")  # hiragana and katakana: Japanese, not Chinese
_CJK = re.compile(r"[぀-ヿ一-鿿]")


def locale_of(text: str) -> str | None:
    """`ja` for a requirement written mostly in Japanese (kana present, and a fifth of its letters CJK)."""
    letters = [ch for ch in text if ch.isalpha()]
    if not letters or not _KANA.search(text):
        return None
    cjk = sum(1 for ch in letters if _CJK.match(ch))
    return "ja" if cjk / len(letters) >= 0.2 else None


def is_ja(locale: str | None) -> bool:
    return bool(locale) and str(locale).split("-")[0] == "ja"


def ja_face(recipe: str | None, heading_font: str | None = None) -> str:
    """The Japanese face for a look: the recipe's, else a mincho under a serif heading font, else Noto Sans JP."""
    if recipe in JA_FACE:
        return JA_FACE[recipe]
    if heading_font and FONTS.get(heading_font) and FONTS[heading_font].category in ("serif", "display"):
        return "Noto Serif JP"
    return DEFAULT_JA_FACE


def _with_face(stack: str, face: str) -> str:
    """A CSS font stack with the Japanese face after its first (Latin) family and the CJK fallbacks after it."""
    first, _, rest = stack.partition(",")
    fallback = JA_SERIF_FALLBACK if JA_FONTS[face].category == "serif" else JA_FALLBACK
    return f'{first.strip()}, "{face}", {fallback}' + (f", {rest.strip()}" if rest.strip() else "")


def ja_imports(face: str) -> list[str]:
    font = JA_FONTS[face]
    return [f"{font.package}/{weight}.css" for weight in font.weights]


def ja_css(theme: dict[str, Any], face: str) -> str:
    """CSS appended to an app's `globals.css` for Japanese: the stacks with the face, then `:lang(ja)` typesetting."""
    fonts = theme.get("fonts") or {}
    body = _with_face(fonts.get("body") or "ui-sans-serif", face)
    heading = _with_face(fonts.get("heading") or fonts.get("body") or "ui-sans-serif", face)
    return (
        f"\n/* Japanese typesetting (Epic 23, Story 23.8): {face} after the Latin face */\n"
        f":root {{\n  --font-body: {body};\n  --font-display: {heading};\n}}\n"
        ":root:lang(ja) body { line-height: 1.8; word-break: auto-phrase; line-break: strict; }\n"
        ":root:lang(ja) :is(h1, h2, h3, h4) {\n"
        "  line-height: 1.5;\n  letter-spacing: normal;\n  text-transform: none;\n"
        '  font-weight: min(var(--heading-weight, 600), 700);\n  font-feature-settings: "palt";\n}\n'
        ':root:lang(ja) :is(.uppercase, [data-slot="badge"]) { text-transform: none; letter-spacing: normal; }\n'
    )


def ja_fonts_ts(base: str, face: str) -> str:
    """`fonts.ts` with the Japanese face's weights imported after the theme's fonts."""
    extra = "".join(f'import "{path}";\n' for path in ja_imports(face))
    return base.replace("\nexport {};\n", f"// Story 23.8: the Japanese face\n{extra}\nexport {{}};\n")
