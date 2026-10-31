"""Design direction for drafted sites (Story 12.6). No LLM.

A requirement is matched to product types in UI UX Pro Max's data (vendored in `design_data/ui-ux-pro-max`, MIT, at
the commit in its SOURCE.json) by a small BM25 ranker. Each match becomes a direction: the product's palette
(`colors.csv`), a font pairing from `typography.csv` inside the bundled font set (17.7), a theme preset, radius and
density mapped from its style, and a home page section order and hero layout mapped from its landing pattern. The
drafting engine sees the top briefs and names one; the theme is then filled from the data, never invented by the
model. Directions whose derived tokens miss WCAG AA (light and dark) are skipped.
"""

import copy
import csv
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from src.modules.shared.domain.frontend_spec import FONTS, THEME_PRESETS, font_category

from .frontend_theme import build_theme, contrast, luminance, mix, on

DATA_DIR = Path(__file__).resolve().parents[2] / "design_data" / "ui-ux-pro-max"
DIRECTIONS = 3
# Another product type is an alternative only when it scores at least half of the best match on two or more terms.
RELATED = 0.5
RELATED_TERMS = 2
# A light suffix stripper (not a full stemmer): photographer / photography, branding / brand, studios / studio.
SUFFIXES = ("ings", "ing", "ers", "er", "ies", "s", "y")
HERO_VARIANTS = ("split", "centered", "banner")
HOME_ROUTE = "/"
_STOP = frozenset(
    "a an and are as at be by for from has have i in is it its me my of on or our so that the their this to us we "
    "with you your will can want need site website page pages app web like also who what which".split()
)

# Our own mapping tables: the data's styles → (preset, radius, density). Effects the renderer does not draw (glass,
# neumorphism, 3D, motion) are not copied; those styles fall back to the nearest flat look.
STYLE_PRESETS: dict[str, tuple[str, str, str]] = {
    "minimalism & swiss style": ("minimal", "sm", "comfortable"),
    "swiss modernism 2.0": ("minimal", "sm", "comfortable"),
    "exaggerated minimalism": ("minimal", "none", "comfortable"),
    "ai-native ui": ("minimal", "md", "comfortable"),
    "flat design": ("minimal", "md", "comfortable"),
    "brutalism": ("minimal", "none", "comfortable"),
    "accessible & ethical": ("corporate", "sm", "comfortable"),
    "vibrant & block-based": ("playful", "lg", "comfortable"),
    "claymorphism": ("playful", "lg", "comfortable"),
    "soft ui evolution": ("playful", "lg", "comfortable"),
    "organic biophilic": ("playful", "lg", "comfortable"),
    "biomimetic / organic 2.0": ("playful", "lg", "comfortable"),
    "aurora ui": ("playful", "lg", "comfortable"),
    "neumorphism": ("playful", "lg", "comfortable"),
    "micro-interactions": ("playful", "md", "comfortable"),
    "data-dense dashboard": ("dashboard", "md", "compact"),
    "heat map & heatmap style": ("dashboard", "md", "compact"),
    "hud / sci-fi fui": ("dashboard", "sm", "compact"),
    "vintage analog / retro film": ("editorial", "sm", "comfortable"),
}
DEFAULT_STYLE = ("minimal", "md", "comfortable")

# Photo lighting, composition and color treatment derived from the preset style (Story 19.3).
PHOTO_STYLES_BY_PRESET: dict[str, str] = {
    "minimal": "warm natural light, soft shadows, muted tones",
    "editorial": "rich contrast, thoughtful composition, warm film tones",
    "playful": "bright saturated colours, high contrast, crisp cheerful light",
    "corporate": "clean professional lighting, balanced exposure, modern setting",
    "dashboard": "crisp focused lighting, clear subject, neutral background",
}

# Landing pattern parts → the catalogue sections of the home page, in order, and the hero layout (17.7 variants).
PATTERN_SECTIONS: dict[str, tuple[list[str], str | None]] = {
    "hero-centric design": (["Hero", "Features", "CallToAction"], "banner"),
    "feature-rich showcase": (["Hero", "Features", "Stats", "CallToAction"], "split"),
    "social proof-focused": (["Hero", "Testimonials", "Stats", "CallToAction"], "split"),
    "storytelling-driven": (["Hero", "RichText", "Gallery", "CallToAction"], "banner"),
    "minimal & direct": (["Hero", "Features", "CallToAction"], "centered"),
    "conversion-optimized": (["Hero", "Features", "Pricing", "Faq", "CallToAction"], "split"),
    "trust & authority": (["Hero", "Stats", "Testimonials", "CallToAction"], "split"),
    "demo": (["Hero", "Gallery", "Features", "CallToAction"], "split"),
    "interactive demo": (["Hero", "Gallery", "Features", "CallToAction"], "split"),
    "interactive product demo": (["Hero", "Gallery", "Features", "CallToAction"], "split"),
    "immersive/interactive experience": (["Hero", "Gallery", "CallToAction"], "banner"),
    "faq/documentation": (["Hero", "Faq", "ContactInfo"], "centered"),
    "filter-heavy grid": (["Hero", "CardGrid"], "centered"),
    "map": (["ContactInfo"], None),
    "feed": (["Hero", "List"], "centered"),
    "thread view": (["DetailView"], None),
    "hero": (["Hero"], "split"),
    "features": (["Features"], None),
    "cta": (["CallToAction"], None),
    "minimal": (["Hero", "Features", "CallToAction"], "centered"),
    "conversion": (["Pricing", "Faq", "CallToAction"], None),
    "hero-centric": (["Hero", "Features", "CallToAction"], "banner"),
    "feature-rich": (["Features", "Stats"], None),
    "social proof": (["Testimonials", "Stats"], None),
    "trust": (["Stats", "Testimonials"], None),
    "storytelling": (["RichText", "Gallery"], None),
}
DEFAULT_ORDER = ["Hero", "Features", "CallToAction"]
# Text on every surface the library uses (Story 17.7): normal text at AA, secondary text at the large-text level.
CONTRAST_PAIRS = [
    ("foreground", "background", 4.5),
    ("card-foreground", "card", 4.5),
    ("primary-foreground", "primary", 4.5),
    ("secondary-foreground", "secondary", 4.5),
    ("muted-foreground", "background", 3.0),
]


# -- data ------------------------------------------------------------------------------------------------------------


@dataclass(frozen=True, eq=False)  # hashed by identity: one loaded copy, cached indexes
class DesignData:
    source: str
    products: list[dict[str, str]]
    reasoning: list[dict[str, str]]
    colors: list[dict[str, str]]
    typography: list[dict[str, str]]
    landing: list[dict[str, str]]
    styles: list[dict[str, str]]


def _rows(name: str, data_dir: Path) -> list[dict[str, str]]:
    with (data_dir / f"{name}.csv").open(newline="", encoding="utf-8") as handle:
        return [
            {key.strip(): (value or "").strip() for key, value in row.items() if key} for row in csv.DictReader(handle)
        ]


@lru_cache
def design_data(data_dir: Path = DATA_DIR) -> DesignData:
    source = json.loads((data_dir / "SOURCE.json").read_text())
    data = DesignData(
        source=f"ui-ux-pro-max@{source['commit'][:12]}",
        products=_rows("products", data_dir),
        reasoning=_rows("ui-reasoning", data_dir),
        colors=_rows("colors", data_dir),
        typography=_rows("typography", data_dir),
        landing=_rows("landing", data_dir),
        styles=_rows("styles", data_dir),
    )
    if not [r["No"] for r in data.products] == [r["No"] for r in data.reasoning] == [r["No"] for r in data.colors]:
        raise ValueError("products, ui-reasoning and colors must list the same product types in the same order")
    return data


# -- ranking ---------------------------------------------------------------------------------------------------------


def stem(word: str) -> str:
    for suffix in SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def tokens(text: str) -> list[str]:
    return [stem(word) for word in re.findall(r"[a-z0-9]+", text.lower()) if word not in _STOP]


def requirement_lead(requirement: str) -> str:
    """The requirement's title and first plain paragraph: where people say what the site is ("a website for a
    two-person design studio"). Later details (page copy, prices, field lists) match unrelated products."""
    title = ""
    for block in (block.strip() for block in re.split(r"\n\s*\n", requirement) if block.strip()):
        if block.startswith("#"):
            title = title or block.splitlines()[0].lstrip("# ")
        elif not re.match(r"^\*\*[^*]+:\*\*", block):  # skip `**Mode:** static` style metadata lines
            return f"{title}\n{block}"
    return title or requirement


def requirement_query(requirement: str) -> list[str]:
    return tokens(requirement_lead(requirement))


class Bm25:
    def __init__(self, documents: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.documents = [Counter(doc) for doc in documents]
        self.lengths = [len(doc) for doc in documents]
        self.average = sum(self.lengths) / max(len(documents), 1)
        frequency = Counter(term for doc in self.documents for term in doc)
        count = len(documents)
        self.idf = {term: math.log(1 + (count - n + 0.5) / (n + 0.5)) for term, n in frequency.items()}
        self.k1, self.b = k1, b

    def scores(self, query: list[str]) -> list[float]:
        terms = set(query)
        out = []
        for doc, length in zip(self.documents, self.lengths, strict=True):
            score = 0.0
            for term in terms & doc.keys():
                tf = doc[term]
                score += (
                    self.idf[term] * tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * length / self.average))
                )
            out.append(score)
        return out


@lru_cache
def _product_index(data: DesignData) -> Bm25:
    # The product type counts most, then its keywords; the reasoning category repeats the type.
    return Bm25([tokens(f"{p['Product Type']} " * 3 + f"{p['Keywords']} " * 2) for p in data.products])


def rank_products(requirement: str, data: DesignData | None = None) -> list[tuple[int, float]]:
    """(product row index, score), best first; ties keep the data's order."""
    data = data or design_data()
    index = _product_index(data)
    scores = index.scores(requirement_query(requirement))
    if not any(scores):
        scores = index.scores(tokens(requirement))
    return sorted(((i, s) for i, s in enumerate(scores) if s > 0), key=lambda item: (-item[1], item[0]))


def matched_terms(requirement: str, index: int, data: DesignData | None = None) -> set[str]:
    data = data or design_data()
    return set(requirement_query(requirement)) & _product_index(data).documents[index].keys()


# -- one direction ---------------------------------------------------------------------------------------------------


def _style(product: dict[str, str], variation: int) -> tuple[str, str, str, str]:
    """(style name, preset, radius, density): the product's first recommended style, or for a variation its
    secondary styles in turn."""
    styles = [product["Primary Style Recommendation"].split("+")[0].strip()]
    styles += [style.strip() for style in product["Secondary Styles"].split(",") if style.strip()]
    name = styles[min(variation, len(styles) - 1)]
    return (name, *STYLE_PRESETS.get(name.lower(), DEFAULT_STYLE))


@lru_cache
def _pairings(data: DesignData) -> tuple[list[dict[str, str]], Bm25]:
    """The `typography.csv` pairings whose fonts are both bundled (17.7) and whose body font is a text face (a few
    rows set body copy in a display or mono font), with their index."""
    rows = [
        row
        for row in data.typography
        if row["Heading Font"] in FONTS
        and row["Body Font"] in FONTS
        and font_category(row["Body Font"]) in ("sans", "serif")
    ]
    return rows, Bm25([tokens(f"{r['Font Pairing Name']} {r['Mood/Style Keywords']} {r['Best For']}") for r in rows])


def _font_pairing(data: DesignData, product: dict[str, str], reasoning: dict[str, str], preset: str, variation: int):
    """The best bundled pairing for the product (the next ones for variations), or the preset's own fonts."""
    rows, index = _pairings(data)
    scores = index.scores(tokens(f"{product['Product Type']} {product['Keywords']} {reasoning['Typography_Mood']}"))
    ranked = [i for i in sorted(range(len(rows)), key=lambda i: (-scores[i], i)) if scores[i] > 0]
    if variation >= len(ranked):
        fonts = THEME_PRESETS[preset]["typography"]
        return f"{preset} preset", fonts["headingFont"], fonts["bodyFont"]
    row = rows[ranked[variation]]
    return row["Font Pairing Name"], row["Heading Font"], row["Body Font"]


def pattern_parts(pattern: str) -> list[str]:
    return [part.strip().lower() for part in re.split(r"\s+\+\s+", pattern) if part.strip()]


def home_order(pattern: str) -> tuple[list[str], str]:
    """The home page's section order and hero layout for a landing pattern (parts joined with ' + ')."""
    order: list[str] = []
    hero: str | None = None
    for part in pattern_parts(pattern):
        sections, variant = PATTERN_SECTIONS.get(part, ([], None))
        hero = hero or variant
        for name in sections:
            if name in order:
                continue
            if "CallToAction" in order and name != "ContactInfo":
                order.insert(order.index("CallToAction"), name)
            else:
                order.append(name)
    order = order or list(DEFAULT_ORDER)
    if "ContactInfo" not in order:
        order.append("ContactInfo")
    return order, hero or "split"


def _landing(data: DesignData, pattern: str) -> list[dict[str, str]]:
    """The `landing.csv` rows naming a part of the pattern (name or alias), for the brief."""
    wanted = set(pattern_parts(pattern)) | {pattern.lower()}
    rows = []
    for row in data.landing:
        names = {row["Pattern Name"].lower(), *(a.strip().lower() for a in row.get("Aliases", "").split(",") if a)}
        if names & wanted:
            rows.append(row)
    return rows


def _split_list(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"\s+\+\s+|,\s*", value) if item.strip()]


def contrast_failures(theme: dict[str, Any]) -> list[str]:
    """Contrast failures of the tokens derived from a theme, light and dark (empty: it passes)."""
    built = build_theme({**theme, "colorScheme": "light-dark"})
    failures = []
    for scheme in ("light", "dark"):
        palette = built[scheme]
        for text, surface, minimum in CONTRAST_PAIRS:
            ratio = contrast(palette[text], palette[surface])
            if ratio is not None and ratio < minimum:
                failures.append(f"{scheme} {text} on {surface}: {ratio:.2f} < {minimum}")
    return failures


def direction(index: int, data: DesignData | None = None, variation: int = 0) -> dict[str, Any]:
    """The design direction of one product row; `variation` > 0 keeps its palette and pattern but takes its next
    secondary style, the next font pairing and another hero layout (alternatives when no other product fits)."""
    data = data or design_data()
    product, reasoning, colors = data.products[index], data.reasoning[index], data.colors[index]
    style, preset, radius, density = _style(product, variation)
    pairing, heading, body = _font_pairing(data, product, reasoning, preset, variation)
    if preset == "minimal" and font_category(heading) in ("serif", "display"):
        preset = "editorial"
    palette = {
        "primary": colors["Primary"].lower(),
        # One accent per page (17.7): the data's secondary brand colour is not used; `secondary` is the neutral
        # surface shadcn expects, as in our presets.
        "secondary": colors["Muted"].lower(),
        "accent": colors["Accent"].lower(),
        "background": colors["Background"].lower(),
        "foreground": colors["Foreground"].lower(),
        "muted": colors["Muted"].lower(),
        "destructive": colors["Destructive"].lower(),
    }
    order, hero = home_order(product["Landing Page Pattern"])
    if variation:
        others = [variant for variant in HERO_VARIANTS if variant != hero]
        hero = others[(variation - 1) % len(others)]
    meta = {
        "productType": product["Product Type"],
        "pattern": product["Landing Page Pattern"],
        "palette": product["Color Palette Focus"] or colors.get("Notes", ""),
        "fontPairing": pairing,
        "source": data.source,
    }
    theme = {
        "style": preset,
        "colorScheme": "dark" if (luminance(palette["background"]) or 1) < 0.2 else "light",
        "colors": palette,
        "typography": {"headingFont": heading, "bodyFont": body, "scale": "default"},
        "radius": radius,
        "density": density,
        "direction": meta,
    }
    photo_style = PHOTO_STYLES_BY_PRESET.get(preset, PHOTO_STYLES_BY_PRESET["minimal"])
    return {
        **meta,
        "label": product["Product Type"] if not variation else f"{product['Product Type']}: {style}",
        "style": style,
        "photoStyle": photo_style,
        "theme": theme,
        "homeOrder": order,
        "heroVariant": hero,
        "avoid": _split_list(reasoning["Anti_Patterns"]),
        "effects": _split_list(reasoning["Key_Effects"]),
        "keywords": product["Keywords"],
        "considerations": product["Key Considerations"],
        "landing": [
            {"pattern": row["Pattern Name"], "sectionOrder": row["Section Order"], "cta": row["Primary CTA Placement"]}
            for row in _landing(data, product["Landing Page Pattern"])
        ],
    }


def directions(requirement: str, count: int = DIRECTIONS, data: DesignData | None = None) -> list[dict[str, Any]]:
    """The best `count` directions for a requirement, each passing the contrast checks: the best matching product
    type, then other product types scoring at least `RELATED` of it (one per palette), then variations of the best
    one. Without any match the data's first row (SaaS, general) stands in, so a draft always gets a direction."""
    data = data or design_data()
    ranked = rank_products(requirement, data)
    top_score = ranked[0][1] if ranked else 0.0
    order = [index for index, _ in ranked] + [i for i in range(len(data.products)) if i not in {i for i, _ in ranked}]
    found: list[dict[str, Any]] = []
    palettes: set[str] = set()

    def add(candidate: dict[str, Any]) -> None:
        key = candidate["theme"]["colors"]["primary"] + candidate["theme"]["colors"]["background"]
        if len(found) < count and key not in palettes and not contrast_failures(candidate["theme"]):
            palettes.add(key)
            found.append(candidate)

    best = next((i for i in order if not contrast_failures(direction(i, data)["theme"])), 0)
    add(direction(best, data))
    for index, score in ranked:
        if (
            index != best
            and score >= RELATED * top_score
            and len(matched_terms(requirement, index, data)) >= RELATED_TERMS
        ):
            add(direction(index, data))
    for variation in range(1, 6):
        if len(found) == count:
            break
        candidate = direction(best, data, variation)
        if not contrast_failures(candidate["theme"]) and candidate["label"] not in {f["label"] for f in found}:
            found.append(candidate)
    return found


# -- applying a direction --------------------------------------------------------------------------------------------


def reorder_sections(sections: list[dict[str, Any]], order: list[str]) -> list[dict[str, Any]]:
    """Sections in the pattern's order; any other section stays right after the one it followed (same rule as the
    UI's `reorderSections`)."""
    rank = {name: position for position, name in enumerate(order)}
    keyed = []
    last = -1
    for position, section in enumerate(sections):
        known = rank.get(section.get("component"))
        if known is not None:
            last = known
            keyed.append(((known, 0, position), section))
        else:
            keyed.append(((last, 1, position), section))
    return [section for _, section in sorted(keyed, key=lambda item: item[0])]


def with_brand(chosen: dict[str, Any], brand: dict[str, Any] | None) -> dict[str, Any]:
    """The direction with the requirement's brand colours and fonts over the data's (12.4: brand words win)."""
    brand = brand if isinstance(brand, dict) else {}
    out = copy.deepcopy(chosen)
    colors = brand.get("colors") if isinstance(brand.get("colors"), dict) else {}
    fonts = brand.get("fonts") if isinstance(brand.get("fonts"), dict) else {}
    theme = out["theme"]
    given = {k: v.lower() for k, v in colors.items() if k in theme["colors"] and isinstance(v, str) and v}
    palette = theme["colors"] | given
    if "background" in given:
        # The data's text and surface colours belong to its own background: on the brand's background, text is
        # near-black or white and the surfaces are the brand's secondary (or a step off the background).
        palette["foreground"] = given.get("foreground") or on(palette["background"])
        surface = given.get("secondary") or given.get("muted")
        surface = surface or mix(palette["background"], palette["foreground"], 0.06) or palette["muted"]
        palette["secondary"] = given.get("secondary") or surface
        palette["muted"] = given.get("muted") or surface
        theme["colorScheme"] = "dark" if (luminance(palette["background"]) or 1) < 0.2 else "light"
    theme["colors"] = palette
    theme["typography"] |= {k: v for k, v in fonts.items() if k in ("headingFont", "bodyFont") and isinstance(v, str)}
    return out


def apply_direction(spec: dict[str, Any], chosen: dict[str, Any]) -> dict[str, Any]:
    """A copy of the FrontendSpec with the direction's theme, home page order and hero layout (same rules as the
    UI's `applyDirection`). The spec's light / dark choice and type scale are kept unless the palette is dark."""
    out = copy.deepcopy(spec)
    current = out.get("theme") if isinstance(out.get("theme"), dict) else {}
    theme = copy.deepcopy(chosen["theme"])
    if theme["colorScheme"] != "dark":
        theme["colorScheme"] = current.get("colorScheme") or "light"
    theme["typography"]["scale"] = (current.get("typography") or {}).get("scale") or "default"
    out["theme"] = theme
    photo_style = chosen.get("photoStyle") or PHOTO_STYLES_BY_PRESET.get(
        theme.get("style", "minimal"), PHOTO_STYLES_BY_PRESET["minimal"]
    )
    if photo_style and isinstance(out.get("assets"), list):
        for asset in out["assets"]:
            if not isinstance(asset, dict):
                continue
            source = str(asset.get("source") or "")
            is_photo = source == "photo" or (source.startswith("upload:") and bool(asset.get("prompt")))
            if is_photo and not asset.get("style"):
                asset["style"] = photo_style
    for page in out.get("pages") or []:
        if page.get("route") != HOME_ROUTE:
            continue
        page["sections"] = reorder_sections(page.get("sections") or [], chosen["homeOrder"])
        for section in page["sections"]:
            if section.get("component") == "Hero":
                section["content"] = {**(section.get("content") or {}), "variant": chosen["heroVariant"]}
                break
    return out


def design_notes(chosen: dict[str, Any]) -> list[dict[str, Any]]:
    """Why the draft looks the way it does, listed with the assumptions."""
    notes = [
        {
            "spec": "frontend",
            "path": "/theme",
            "message": (
                f"Design direction: {chosen['productType']} ({chosen['pattern']}); palette {chosen['palette']}; "
                f"fonts {chosen['fontPairing']} ({chosen['theme']['typography']['headingFont']} / "
                f"{chosen['theme']['typography']['bodyFont']}); from {chosen['source']}"
            ),
        }
    ]
    if chosen["avoid"]:
        notes.append({"spec": "frontend", "path": "/theme", "message": "Avoid: " + ", ".join(chosen["avoid"]).lower()})
    if chosen["effects"]:
        notes.append(
            {
                "spec": "frontend",
                "path": "/theme",
                "message": "Key effects (not drawn by the section renderer): " + ", ".join(chosen["effects"]).lower(),
            }
        )
    return notes


def brief_markdown(found: list[dict[str, Any]]) -> str:
    """`.bga/design.md` for the drafting engine: the ranked design briefs."""
    lines = [
        "# Design briefs",
        "",
        "Ranked for this requirement from UI UX Pro Max's data. Pick the brief that fits the requirement best (the",
        "first unless another is clearly closer) and name its product type in the notes. The theme, the home page's",
        "section order and the hero layout are filled from it after you finish.",
        "",
    ]
    for position, item in enumerate(found, 1):
        theme = item["theme"]
        lines += [
            f"## {position}. {item['productType']}",
            "",
            f"- Keywords: {item['keywords']}",
            f"- Landing pattern: {item['pattern']} → home sections: {', '.join(item['homeOrder'])} "
            f"(Hero `{item['heroVariant']}`)",
            *(f"  - {row['pattern']}: {row['sectionOrder']} (CTA: {row['cta']})" for row in item["landing"]),
            f"- Palette: {item['palette']} (primary {theme['colors']['primary']}, accent {theme['colors']['accent']}, "
            f"background {theme['colors']['background']})",
            f"- Fonts: {item['fontPairing']} "
            f"({theme['typography']['headingFont']} / {theme['typography']['bodyFont']})",
            f"- Style: {item['style']} → preset `{theme['style']}`",
            f"- Considerations: {item['considerations']}",
            f"- Avoid: {', '.join(item['avoid']) or '-'}",
            "",
        ]
    return "\n".join(lines)


def pick(found: list[dict[str, Any]], product_type: Any) -> int:
    """Index of the brief the engine named (by product type), else 0."""
    if isinstance(product_type, str):
        for position, item in enumerate(found):
            if item["productType"].lower() == product_type.strip().lower():
                return position
    return 0
