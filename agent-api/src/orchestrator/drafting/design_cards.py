"""Direction cards (Story 20.4) and content-led home pages (Story 20.9). No LLM.

The drafting engine writes three **direction cards** in `notes.json` (`design.cards`): an idea from the product, a
tone on five scales, a hero layout, fonts, colours with where they come from, a key visual, section forms, a page
rhythm, what the direction gives up, how well it fits (1 = best) and, from 20.9, the home page it composes from the
drafted sections (`home`: section ids). Code checks and fills each card (bundled fonts, known layouts and forms,
colours that parse and pass AA in light and dark), turns the tone into theme tokens (`design_tone.py`) and runs the
**difference test** (epic D3): any two directions share at most one of hero layout, heading font, hue family and key
visual; the three hero layouts differ (so at most one `split`); at least one home page off the category's usual
order; any two home pages differ in their first three sections. A card that fails is asked again
(`repair_direction`), and after that code fixes it.

UI UX Pro Max (12.6) is the floor: its best match describes the category default in the fact pack, its palette
replaces colours that fail contrast twice, and its directions stand in when the engine wrote no usable cards.

A filled direction keeps the shape of 12.6's directions (the review and the UI apply both) plus the card's fields;
`apply_direction` in `design_direction.py` applies either kind to a spec.
"""

import colorsys
import copy
import random
import re
from itertools import combinations
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from pydantic.alias_generators import to_camel

from src.modules.shared.domain.frontend_spec import FONTS, SECTION_PROPS, closest_font, font_category
from src.modules.shared.domain.frontend_spec.copy_rules import phrase_list

from ..frontend.motion import FEELS, SIGNATURES
from ..frontend.theme import _hex, _rgb, contrast, luminance, mix, on
from .design_direction import FORM_SECTIONS, HOME_ROUTE, PHOTO_STYLES_BY_PRESET, contrast_failures, with_brand
from .design_diversity import VISUAL_FIELDS, difference_problems, hue_family, off_default, shared_fields
from .design_tone import SCALES, apply_tone, icon_style, motion_feel, normalize_tone

DIRECTIONS = 3
MAX_SEED = 1_000_000
ENGINES = ("material", "scene", "character", "tradition", "medium", "convention")
KEY_VISUALS = ("photo", "illustration", "type", "product", "pattern")
RHYTHMS = ("uniform", "alternate", "dividers")
ICON_SETS = ("lucide", "phosphor", "none")
ICON_WEIGHTS = ("thin", "light", "regular", "bold", "fill", "duotone")
ICON_TREATMENTS = ("plain", "tile")
# Layouts that show no image, for a key visual of `type`; the others carry an image.
TYPE_LAYOUTS = ("type", "centered", "vertical")
FIRST = 3  # home pages differ in their first three sections (20.9)
HUE_STEPS = (60, 120, 180, 240, 300)


def _choices(component: str, field: str) -> tuple[str, ...]:
    schema = SECTION_PROPS[component].model_json_schema(by_alias=True)["properties"][field]
    enum = schema.get("enum") or next((s["enum"] for s in schema.get("anyOf", []) if "enum" in s), [])
    return tuple(enum)


HERO_LAYOUTS = _choices("Hero", "variant")
FORMS = {name: _choices(name, "form") for name in FORM_SECTIONS}


# -- card ------------------------------------------------------------------------------------------------------------


class _Lenient(BaseModel):
    """What the engine wrote, read leniently: unknown values are fixed with a note, not rejected."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")


class CardFonts(_Lenient):
    heading: str = ""
    body: str = ""


class CardColors(_Lenient):
    primary: str = ""
    background: str = ""
    foreground: str | None = None
    muted: str | None = None
    accent: str | None = None
    source: str = ""


class Card(_Lenient):
    name: str = Field(default="", max_length=80)
    concept: str = Field(default="", max_length=300)
    engine: str = ""
    evidence: str = ""
    tone: dict[str, Any] = {}
    hero_layout: str = "split"
    section_forms: dict[str, str] = {}
    rhythm: str = "uniform"
    fonts: CardFonts = CardFonts()
    colors: CardColors = CardColors()
    key_visual: str = "photo"
    gives_up: str = Field(default="", max_length=300)
    fit: int = 2
    home: list[str] | None = None
    # Stories 20.5, 20.6: optional; without them the tone decides (`design_tone.icon_style`, `motion_feel`) and the
    # home page's content the signature moment.
    icons: dict[str, str] = {}
    motion: str = ""
    signature: str = ""

    @field_validator("name", "concept", "gives_up", mode="before")
    @classmethod
    def _clip(cls, value: Any, info: Any) -> Any:
        """Long text is cut at its limit, not rejected."""
        limit = 80 if info.field_name == "name" else 300
        return value[:limit].rstrip() if isinstance(value, str) else value

    @model_validator(mode="before")
    @classmethod
    def _motion_object(cls, data: Any) -> Any:
        """`motion` may come in the theme's shape, `{"feel", "signature"}`."""
        if isinstance(data, dict) and isinstance(data.get("motion"), dict):
            motion = data["motion"]
            data = {**data, "motion": motion.get("feel", "")}
            if not data.get("signature") and motion.get("signature"):
                data["signature"] = motion["signature"]
        return data


def read_cards(design: Any) -> tuple[list[Card], list[str]]:
    """The cards in `notes.json`'s `design.cards` (the first three, in the engine's order, so a card keeps its number
    for a repair) and notes on the ones dropped."""
    raw = design.get("cards") if isinstance(design, dict) else None
    if not isinstance(raw, list):
        return [], []
    cards, notes = [], []
    for position, item in enumerate(raw, 1):
        if not isinstance(item, dict):
            notes.append(f"Card {position} is not an object; left out")
            continue
        try:
            cards.append(Card.model_validate(item))
        except ValidationError as exc:
            # One unreadable field costs that field (its default), not the whole card.
            bad = {str(error["loc"][0]) for error in exc.errors() if error["loc"]}
            kept = {key: value for key, value in item.items() if key not in bad}
            try:
                cards.append(Card.model_validate(kept))
            except ValidationError as again:
                notes.append(f"Card {position} could not be read ({str(again).splitlines()[0]}); left out")
                continue
            notes.append(f"Card {position}: {', '.join(sorted(bad))} could not be read; the default is used")
    return cards[:DIRECTIONS], notes


# -- the drafted home page (20.9) ------------------------------------------------------------------------------------


def home_page(spec: dict[str, Any]) -> dict[str, Any] | None:
    return next((page for page in spec.get("pages") or [] if page.get("route") == HOME_ROUTE), None)


def home_pool(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """The drafted home page's sections (with ids): what each direction composes its home page from."""
    page = home_page(spec)
    return [copy.deepcopy(s) for s in (page or {}).get("sections") or [] if isinstance(s, dict) and s.get("id")]


def _hero_id(pool: list[dict[str, Any]]) -> str | None:
    return next((s["id"] for s in pool if s.get("component") == "Hero"), None)


def compose(home: list[str] | None, pool: list[dict[str, Any]], required: list[str]) -> list[str]:
    """A card's home page as section ids: known ids of the pool in the card's order, the hero first, every required
    section kept (at its place in the pool's order). Without a `home` the whole pool in its order."""
    ids = [s["id"] for s in pool]
    if not home:
        return ids
    chosen = list(dict.fromkeys(i for i in home if i in ids))
    hero = _hero_id(pool)
    if hero is not None:
        chosen = [hero, *(i for i in chosen if i != hero)]
    for needed in (i for i in required if i in ids and i not in chosen):
        later = [i for i in ids[ids.index(needed) + 1 :] if i in chosen]
        chosen.insert(chosen.index(later[0]) if later else len(chosen), needed)
    return chosen or ids


def components(home: list[str], pool: list[dict[str, Any]]) -> list[str]:
    by_id = {s["id"]: s.get("component", "") for s in pool}
    return [by_id[i] for i in home if i in by_id]


# -- fill ------------------------------------------------------------------------------------------------------------


def _color(value: str | None) -> str | None:
    rgb = _rgb(value or "")
    return _hex(rgb) if rgb is not None else None


def preset_for(tone: dict[str, int], heading: str) -> str:
    """The theme preset nearest to a tone, for the parts presets still drive (photo style, editor defaults)."""
    if tone["energy"] >= 4 and tone["seriousness"] <= 2:
        return "playful"
    if tone["density"] >= 4 and tone["seriousness"] >= 4:
        return "dashboard"
    if font_category(heading) in ("serif", "display"):
        return "editorial"
    if tone["seriousness"] >= 4:
        return "corporate"
    return "minimal"


def _palette(colors: CardColors, floor: dict[str, str]) -> dict[str, str] | None:
    primary, background = _color(colors.primary), _color(colors.background)
    if primary is None or background is None:
        return None
    foreground = _color(colors.foreground) or on(background)
    surface = _color(colors.muted) or mix(background, foreground, 0.06) or floor["muted"]
    return {
        "primary": primary,
        "secondary": surface,
        "accent": _color(colors.accent) or primary,
        "background": background,
        "foreground": foreground,
        "muted": surface,
        "destructive": floor.get("destructive") or "#dc2626",
    }


def _shift(color: str, lightness: float = 0.0, hue: float = 0.0) -> str:
    rgb = _rgb(color)
    if rgb is None:
        return color
    h, light, s = colorsys.rgb_to_hls(*rgb)
    return _hex(colorsys.hls_to_rgb((h + hue / 360) % 1, max(0.0, min(1.0, light + lightness)), s))


def fix_contrast(theme: dict[str, Any]) -> bool:
    """Makes the primary readable within its hue (darker, then lighter, in small steps) and the text the readable
    one for the background; True when the theme then passes in light and dark."""
    if not contrast_failures(theme):
        return True
    colors = theme["colors"]
    if (contrast(colors["foreground"], colors["background"]) or 0) < 4.5:
        colors["foreground"] = on(colors["background"])
        if not contrast_failures(theme):
            return True
    original = colors["primary"]
    for step in range(1, 11):
        for sign in (-1, 1):
            colors["primary"] = _shift(original, sign * step * 0.04)
            if colors["accent"] == original:
                colors["accent"] = colors["primary"]
            if not contrast_failures(theme):
                return True
    colors["primary"] = original
    return False


def card_icons(card: Card, tone: dict[str, int], notes: list[str]) -> dict[str, str]:
    """The card's icon style, completed from the tone; Lucide cannot fill, so fill / duotone take Phosphor."""
    style = icon_style(tone) | {
        key: value
        for key, value in card.icons.items()
        if value in {"set": ICON_SETS, "weight": ICON_WEIGHTS, "treatment": ICON_TREATMENTS}.get(key, ())
    }
    if style["set"] == "lucide" and style["weight"] in ("fill", "duotone"):
        style["set"] = "phosphor"
        notes.append(f"icons: {style['weight']} needs the phosphor set")
    return style


def _has_figures(pool: list[dict[str, Any]]) -> bool:
    for section in pool:
        items = (section.get("content") or {}).get("items") if section.get("component") == "Stats" else None
        if any(isinstance(i, dict) and re.search(r"\d", str(i.get("value", ""))) for i in items or []):
            return True
    return False


def signature(wanted: str, layout: str, pool: list[dict[str, Any]]) -> str:
    """The one stronger moment (Story 20.6): the card's choice when the home page can show it, else from the content:
    count-up for figures, a rising headline for type-led layouts, an unmasking image for image-led ones, else the
    navigation indicator."""
    hero = next((s for s in pool if s.get("component") == "Hero"), None)
    content = (hero or {}).get("content") or {}
    image = bool(content.get("image") or content.get("images")) and layout not in TYPE_LAYOUTS
    possible = {
        "countUp": _has_figures(pool),
        "headlineRise": hero is not None,
        "imageUnmask": image,
        "indicator": True,
    }
    if wanted in SIGNATURES and possible[wanted]:
        return wanted
    if possible["countUp"]:
        return "countUp"
    if hero is not None and layout in TYPE_LAYOUTS:
        return "headlineRise"
    return "imageUnmask" if image else "indicator"


def fill_card(
    card: Card, floor: dict[str, Any], pool: list[dict[str, Any]], required: list[str], seed: int
) -> tuple[dict[str, Any], list[str]]:
    """A checked, filled direction from a card, with notes on what code changed."""
    notes: list[str] = []
    name = card.name.strip() or "Untitled direction"
    tone = normalize_tone(card.tone)
    heading = card.fonts.heading if card.fonts.heading in FONTS else closest_font(card.fonts.heading or "Inter")
    body = card.fonts.body if card.fonts.body in FONTS else closest_font(card.fonts.body or "Inter")
    if font_category(body) not in ("sans", "serif"):
        body = "Inter"
    if (heading, body) != (card.fonts.heading, card.fonts.body):
        notes.append(f"fonts {card.fonts.heading or '-'} / {card.fonts.body or '-'} → {heading} / {body} (bundled)")
    layout = card.hero_layout if card.hero_layout in HERO_LAYOUTS else "split"
    if layout != card.hero_layout:
        notes.append(f"hero layout '{card.hero_layout}' is unknown; split")
    key_visual = card.key_visual if card.key_visual in KEY_VISUALS else "photo"
    hero = next((s for s in pool if s.get("component") == "Hero"), None)
    hero_content = (hero or {}).get("content") or {}
    images = {i for i in [hero_content.get("image"), *(hero_content.get("images") or [])] if i}
    if layout == "collage" and len(images) < 2:
        layout = "stacked"
        notes.append("the collage hero needs two images and the hero has fewer; stacked")
    if key_visual == "type" and layout not in TYPE_LAYOUTS:
        notes.append(f"a type-led first screen cannot use the {layout} layout; type")
        layout = "type"
    elif layout == "type" and key_visual != "type":
        key_visual = "type"
    forms = {k: v for k, v in card.section_forms.items() if k in FORMS and v in FORMS[k]}
    rhythm = card.rhythm if card.rhythm in RHYTHMS else "uniform"
    floor_colors = floor["theme"]["colors"]
    palette = _palette(card.colors, floor_colors)
    source = card.colors.source.strip()
    if palette is None:
        palette = dict(floor_colors)
        source = f"{floor['productType']} palette (the card's colours did not parse)"
        notes.append("colours did not parse; the category palette is used")
    preset = preset_for(tone, heading)
    theme: dict[str, Any] = {
        "style": preset,
        "colorScheme": "dark" if (luminance(palette["background"]) or 1) < 0.2 else "light",
        "colors": dict(palette),
        "typography": {"headingFont": heading, "bodyFont": body, "scale": "default"},
        "radius": "md",
        "density": "comfortable",
    }
    theme = apply_tone(theme, tone)
    theme["icons"] = card_icons(card, tone, notes)
    feel = card.motion if card.motion in FEELS or card.motion == "none" else motion_feel(tone)
    theme["motion"] = {"feel": feel, "signature": signature(card.signature, layout, pool) if feel != "none" else "none"}
    if not fix_contrast(theme):
        theme["colors"] = dict(floor_colors)
        theme["colorScheme"] = "dark" if (luminance(floor_colors["background"]) or 1) < 0.2 else "light"
        source = f"{floor['productType']} palette (the card's colours missed AA contrast)"
        notes.append("colours missed AA contrast in light or dark; the category palette is used")
    else:
        for key in ("primary", "foreground"):
            if theme["colors"][key] != palette[key]:
                notes.append(f"{key} {palette[key]} → {theme['colors'][key]} for AA contrast")
    home = compose(card.home, pool, required)
    direction = {
        "label": name,
        "name": name,
        "concept": card.concept.strip(),
        "engine": card.engine if card.engine in ENGINES else None,
        "evidence": card.evidence.strip(),
        "givesUp": card.gives_up.strip(),
        "fit": card.fit,
        "tone": tone,
        "keyVisual": key_visual,
        "productType": floor["productType"],
        "pattern": floor["pattern"],
        "palette": source or "from the card",
        "fontPairing": f"{heading} / {body}",
        "source": "card",
        "style": card.concept.strip().rstrip(".") or name,  # drawings: "<style>, flat vector shapes"
        "photoStyle": PHOTO_STYLES_BY_PRESET.get(preset, PHOTO_STYLES_BY_PRESET["minimal"]),
        "theme": theme,
        "home": home,
        "homeOrder": components(home, pool),
        "heroVariant": layout,
        "sectionForms": forms,
        "rhythm": rhythm,
        "avoid": floor.get("avoid", []),
        "effects": [],
        "notes": notes,
    }
    _set_direction_meta(direction, seed)
    return direction, notes


def floor_direction(floor: dict[str, Any], pool: list[dict[str, Any]], seed: int) -> dict[str, Any]:
    """A UI UX Pro Max direction (12.6) as a stand-in: its theme and hero layout, the drafted home page as it is
    (20.9: the category's order no longer reorders pages)."""
    out = copy.deepcopy(floor)
    home = [s["id"] for s in pool]
    out |= {
        "name": out["label"],
        "concept": "",
        "givesUp": "",
        "fit": 3,
        "tone": None,
        "keyVisual": None,
        "home": home,
        "homeOrder": components(home, pool),
        "notes": [],
    }
    _set_direction_meta(out, seed)
    return out


def _set_direction_meta(direction: dict[str, Any], seed: int) -> None:
    meta = {
        "productType": direction["productType"],
        "pattern": direction["pattern"],
        "palette": direction["palette"],
        "fontPairing": direction["fontPairing"],
        "source": direction["source"],
    }
    if direction["source"] == "card":
        meta |= {
            "name": direction["name"],
            "concept": direction["concept"] or None,
            "engine": direction["engine"],
            "tone": direction["tone"],
            "keyVisual": direction["keyVisual"],
            "givesUp": direction["givesUp"] or None,
            "seed": seed,
        }
    direction["theme"]["direction"] = {k: v for k, v in meta.items() if v is not None}


# -- difference test -------------------------------------------------------------------------------------------------


def fields(direction: dict[str, Any], hero_present: bool = True) -> dict[str, str]:
    theme = direction["theme"]
    return {
        "hero": direction["heroVariant"] if hero_present else "none",
        "headingFont": theme["typography"]["headingFont"],
        "hueFamily": hue_family(theme["colors"]["primary"]),
        "keyVisual": direction.get("keyVisual") or "photo",
    }


def _compare(fixed: set[str], hero_present: bool) -> tuple[str, ...]:
    """The visual fields the test compares: not those the brand fixes; on a home page without a hero (an app's
    dashboard) only the heading font and the hue, since no hero layout or key visual is shown."""
    return tuple(f for f in compared_fields(hero_present) if f not in fixed)


def compared_fields(hero_present: bool) -> tuple[str, ...]:
    return VISUAL_FIELDS if hero_present else ("headingFont", "hueFamily")


def composition_problems(homes: list[list[str]], pool_size: int) -> list[str]:
    """20.9: any two home pages differ in their first three sections (set or order), when the pool allows it."""
    if pool_size < FIRST:
        return []
    return [
        f"directions {i + 1} and {j + 1} open their home pages with the same sections"
        for (i, first), (j, second) in combinations(enumerate(homes), 2)
        if first[:FIRST] == second[:FIRST]
    ]


def layout_problems(heroes: list[str]) -> list[str]:
    """The three directions show three different hero layouts: the layout decides the first screen more than any
    other field (Checkpoint C: two `stacked` heroes with different fonts and hues still looked 98.7% alike)."""
    return [
        f"directions {i + 1} and {j + 1} use the same hero layout ({first})"
        for (i, first), (j, second) in combinations(enumerate(heroes), 2)
        if first == second and first != "none"
    ]


def problems(
    directions: list[dict[str, Any]], default: list[str], pool: list[dict[str, Any]], fixed: set[str]
) -> list[str]:
    """Everything the difference test finds over a draft's directions (empty: it passes)."""
    hero_present = _hero_id(pool) is not None
    compare = _compare(fixed, hero_present)
    found = difference_problems(
        [fields(d, hero_present) for d in directions],
        [d["homeOrder"] for d in directions],
        default,
        compare,
    )
    heroes = [d["heroVariant"] for d in directions] if hero_present else []
    return found + layout_problems(heroes) + composition_problems([d["home"] for d in directions], len(pool))


def failing_card(directions: list[dict[str, Any]], fixed: set[str], pool: list[dict[str, Any]]) -> int | None:
    """The card to ask again: the later one of the first pair that shares too much, else the second split."""
    hero_present = _hero_id(pool) is not None
    compare = _compare(fixed, hero_present)
    for i, j in combinations(range(len(directions)), 2):
        a, b = fields(directions[i], hero_present), fields(directions[j], hero_present)
        same_home = len(pool) >= FIRST and directions[i]["home"][:FIRST] == directions[j]["home"][:FIRST]
        same_layout = hero_present and a["hero"] == b["hero"]
        if len(shared_fields(a, b, compare)) > 1 or same_home or same_layout:
            return j
    splits = [i for i, d in enumerate(directions) if d["heroVariant"] == "split"]
    return splits[1] if len(splits) > 1 else None


def _set_hero(direction: dict[str, Any], used: set[str]) -> bool:
    if direction.get("keyVisual") == "type":
        allowed = TYPE_LAYOUTS
    else:
        allowed = tuple(layout for layout in HERO_LAYOUTS if layout not in ("type", "collage"))
    for layout in allowed:
        if layout not in used:
            direction["heroVariant"] = layout
            return True
    return False


def _set_font(direction: dict[str, Any], used: set[str]) -> bool:
    typography = direction["theme"]["typography"]
    category = font_category(typography["headingFont"])
    for name, font in FONTS.items():
        if font.category == category and name not in used and name != typography["bodyFont"]:
            typography["headingFont"] = name
            direction["fontPairing"] = f"{name} / {typography['bodyFont']}"
            return True
    return False


def _set_hue(direction: dict[str, Any], used: set[str]) -> bool:
    colors = direction["theme"]["colors"]
    original = colors["primary"]
    for step in HUE_STEPS:
        candidate = _shift(original, hue=step)
        if hue_family(candidate) in used:
            continue
        trial = copy.deepcopy(direction["theme"])
        trial["colors"]["primary"] = candidate
        if trial["colors"]["accent"] == original:
            trial["colors"]["accent"] = candidate
        if fix_contrast(trial):
            direction["theme"]["colors"] = trial["colors"]
            return True
    return False


def _set_key_visual(direction: dict[str, Any], used: set[str]) -> bool:
    for kind in ("illustration", "pattern", "product", "photo"):
        if kind not in used and direction["heroVariant"] not in ("type",):
            direction["keyVisual"] = kind
            return True
    return False


SETTERS = {"hero": _set_hero, "headingFont": _set_font, "hueFamily": _set_hue, "keyVisual": _set_key_visual}


def _reorder(home: list[str], taken: list[list[str]], required: list[str], pool: list[dict[str, Any]]) -> list[str]:
    """Another order (or set) of a home page whose first three sections differ from the others'."""
    hero = _hero_id(pool)
    head = [hero] if hero in home else []
    rest = [i for i in home if i != hero]
    candidates = [rest[k:] + rest[:k] for k in range(1, len(rest))] + [list(reversed(rest))]
    optional = [i for i in rest if i not in required]
    candidates += [[i for i in rest if i != drop] for drop in optional]
    for candidate in candidates:
        composed = head + candidate
        if all(composed[:FIRST] != other[:FIRST] for other in taken):
            return composed
    return home


def code_fix(
    directions: list[dict[str, Any]],
    default: list[str],
    pool: list[dict[str, Any]],
    required: list[str],
    fixed: set[str],
) -> list[str]:
    """Fixes what the engine left (D3): the later direction of a pair takes the next free hero layout, a font of the
    same kind, a hue ≥ 60° away or another key visual; a repeated hero layout moves; home pages are reordered.
    Returns notes."""
    notes: list[str] = []
    hero_present = _hero_id(pool) is not None
    compare = _compare(fixed, hero_present)
    for _ in range(4):
        changed = False
        for i, j in combinations(range(len(directions)), 2):
            shared = shared_fields(fields(directions[i], hero_present), fields(directions[j], hero_present), compare)
            for field in shared[1:]:
                others = [fields(d, hero_present)[field] for k, d in enumerate(directions) if k != j]
                if SETTERS[field](directions[j], set(others)):
                    notes.append(f"Direction {j + 1} ({directions[j]['name']}): {field} changed to differ")
                    changed = True
        for k in range(1, len(directions) if hero_present else 0):
            if directions[k]["heroVariant"] in {d["heroVariant"] for d in directions[:k]}:
                others = {d["heroVariant"] for m, d in enumerate(directions) if m != k}
                if _set_hero(directions[k], others):
                    notes.append(f"Direction {k + 1} ({directions[k]['name']}): its own hero layout")
                    changed = True
        if not changed:
            break
    for j in range(1, len(directions)):
        taken = [d["home"] for d in directions[:j]]
        if len(pool) >= FIRST and any(directions[j]["home"][:FIRST] == other[:FIRST] for other in taken):
            directions[j]["home"] = _reorder(directions[j]["home"], taken, required, pool)
            notes.append(f"Direction {j + 1} ({directions[j]['name']}): home page reordered to differ")
    homes = [components(d["home"], pool) for d in directions]
    if default and pool and not any(off_default(home, default) for home in homes):
        last = directions[-1]
        last["home"] = _reorder(last["home"], [last["home"]], required, pool)
        notes.append(f"Direction {len(directions)} ({last['name']}): home page moved off the category's usual order")
    for direction in directions:
        direction["homeOrder"] = components(direction["home"], pool)
        if direction["source"] == "card":
            direction["theme"]["direction"]["keyVisual"] = direction["keyVisual"]
            direction["theme"]["direction"]["fontPairing"] = direction["fontPairing"]
    return notes


# -- seeds -----------------------------------------------------------------------------------------------------------


def new_seed() -> int:
    return random.SystemRandom().randrange(1, MAX_SEED)


# -- fact pack -------------------------------------------------------------------------------------------------------

HERO_NOTES = {
    "split": "text on one side, the image on the other",
    "centered": "one sentence or object centred in wide space",
    "banner": "a full-bleed image (or the primary colour) with the text over it",
    "stage": "the image is the screen; headline and button on its lower edge",
    "type": "type is the image: an oversized headline, no image",
    "stacked": "a full-width headline, then a wide image below",
    "collage": "headline plus 2–4 images in an asymmetric grid (needs `images`)",
    "vertical": "a vertical display label beside the headline",
}


def fact_pack(floor: dict[str, Any] | None, seed: int, mode: str) -> str:
    """`.bga/design.md` for the drafting engine: the category default to move away from, what the renderer can draw,
    and the variation seed."""
    lines = ["# Design facts", "", f"Variation: {seed} (a different number means: try different ideas).", ""]
    if floor is not None:
        theme = floor["theme"]
        lines += [
            "## The category default (the look to move away from)",
            "",
            f"UI UX Pro Max files this requirement under **{floor['productType']}**. Its default site: palette "
            f"{floor['palette']} (primary {theme['colors']['primary']}, background {theme['colors']['background']}), "
            f"fonts {theme['typography']['headingFont']} / {theme['typography']['bodyFont']}, landing pattern "
            f"{floor['pattern']} (home: {', '.join(floor['homeOrder'])}). At most one direction may stay close to it.",
            f"- Anti-patterns for this category: {', '.join(floor['avoid']) or '-'}",
            "",
        ]
    by_category: dict[str, list[str]] = {}
    for name, font in FONTS.items():
        by_category.setdefault(font.category, []).append(name)
    lines += [
        "## What the renderer draws",
        "",
        "Hero layouts (`heroLayout`):",
        *(f"- `{name}`: {HERO_NOTES.get(name, '')}" for name in HERO_LAYOUTS),
        "",
        "Section forms (`sectionForms`, optional): "
        + "; ".join(f"{name}: {' | '.join(choices)}" for name, choices in FORMS.items())
        + ". Page rhythm (`rhythm`): uniform | alternate (muted bands) | dividers (hairlines).",
        "",
        "Bundled fonts (`fonts.heading`, `fonts.body`; body is sans or serif):",
        *(f"- {category}: {', '.join(names)}" for category, names in by_category.items()),
        "",
        "Key visual (`keyVisual`, what carries the first screen): "
        + " | ".join(KEY_VISUALS)
        + ". `type` goes with the type, centered or vertical layouts.",
        "",
        "Tone (`tone`, 1–5 each): " + ", ".join(SCALES) + ". It sets colour area, type scale, radius, surfaces,"
        " density and heading weight and case; you do not set those yourself.",
        "",
        "Icons (`icons`, optional): sets lucide | phosphor | none; weights thin | light | regular | bold | fill |"
        " duotone (fill and duotone: phosphor); treatment plain | tile. Motion (`motion`, optional): "
        + " | ".join(["none", *FEELS])
        + "; one signature moment (`signature`): "
        + " | ".join(SIGNATURES)
        + ". Left out, both follow the tone.",
        "",
        f"Stock phrases never to use in headings or buttons: {phrase_list()}.",
    ]
    return "\n".join(lines) + "\n"


def design_record(
    directions: list[dict[str, Any]], selected: int, seed: int, pool: list[dict[str, Any]], required: list[str]
) -> dict[str, Any]:
    """What the draft keeps (`spec_drafts.design`)."""
    return {"selected": selected, "directions": directions, "seed": seed, "pool": pool, "required": required}


def best_fit(directions: list[dict[str, Any]]) -> int:
    """Q25: the direction the engine ranks best for the requirement (lowest `fit`), the first on ties."""
    return min(range(len(directions)), key=lambda i: (directions[i].get("fit") or 3, i))


def card_directions(
    cards: list[Card],
    floors: list[dict[str, Any]],
    pool: list[dict[str, Any]],
    required: list[str],
    seed: int,
    brand: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Filled directions: the cards, then the floor's directions for any missing (at least one direction always)."""
    notes: list[str] = []
    out = []
    for card in cards:
        direction, _ = fill_card(card, floors[0], pool, required, seed)
        out.append(with_brand(direction, brand))
    if len(out) < DIRECTIONS:
        missing = DIRECTIONS - len(out)
        if cards:
            notes.append(f"The engine wrote {len(cards)} usable card(s); {missing} from the category data")
        for floor in floors[: missing if cards else DIRECTIONS]:
            out.append(with_brand(floor_direction(floor, pool, seed), brand))
    return out, notes


def brand_fixed(brand: dict[str, Any] | None) -> set[str]:
    """Visual fields the requirement fixes for every direction."""
    brand = brand if isinstance(brand, dict) else {}
    fixed = set()
    if isinstance(brand.get("colors"), dict) and brand["colors"].get("primary"):
        fixed.add("hueFamily")
    if isinstance(brand.get("fonts"), dict) and brand["fonts"].get("headingFont"):
        fixed.add("headingFont")
    return fixed
