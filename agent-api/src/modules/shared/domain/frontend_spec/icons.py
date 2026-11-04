"""Content icons (Story 20.5): references, the icon index and the resolver. No LLM.

An item's `icon` is a reference to a real icon (`lucide:Truck`, `phosphor:Truck`) or an **intent** the drafter writes
(`intent:fast delivery`). The site's `theme.icons.set` decides which set is drawn, so a reference or intent is resolved
when the site is planned, against that set: an intent by ranking the set's index (name words count twice, then tags
and categories; BM25), a reference to the other set by its name's words. Switching direction (a different set) keeps
every icon meaningful without touching the items.

The index (`templates/nextjs_base/icon-index.json`) is written by `scripts/icon-index.mjs` from the pinned base's
lucide-react and @phosphor-icons/react (`make frontend-base`, or `make icon-index` for the index alone). Lucide
icons are keyed by file name (`truck`), Phosphor icons by component name (`Truck`); references always use the
component name. Lucide's old names (`alert-triangle`) map to the current ones in `lucide.aliases`.
"""

import difflib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from src.libs.search import Bm25, stem

ICON_INDEX_FILE = Path(__file__).resolve().parents[5] / "templates" / "nextjs_base" / "icon-index.json"
ICON_REF = r"^(lucide|phosphor):[A-Z][A-Za-z0-9]*$|^intent:[^\n]{2,80}$"
IconSet = Literal["lucide", "phosphor", "none"]
SETS = ("lucide", "phosphor")
# Small marks the library draws itself (checks, contact details), in each set. With the set "none" the Lucide form
# draws the marks that carry meaning (checks); decorative ones (contact details) are left out.
GLYPHS: dict[str, dict[str, str]] = {
    "check": {"lucide": "Check", "phosphor": "Check"},
    "minus": {"lucide": "Minus", "phosphor": "Minus"},
    "mail": {"lucide": "Mail", "phosphor": "Envelope"},
    "phone": {"lucide": "Phone", "phosphor": "Phone"},
    "mapPin": {"lucide": "MapPin", "phosphor": "MapPin"},
    "clock": {"lucide": "Clock", "phosphor": "Clock"},
}
NAME_WEIGHT = 2
EXACT_BONUS = 1.5
HEAD_WEIGHT = 2  # the last word of an intent is usually its noun ("fast delivery")
_STOP = frozenset("a an and for of the to with your our my in on at by".split())
# Words small-business sites use, mapped to the objects icons draw. Added to the intent's own words.
OBJECTS: dict[str, str] = {
    "hours": "clock time", "opening": "clock", "schedule": "calendar clock", "appointment": "calendar",
    "booking": "calendar", "book": "calendar", "reservation": "calendar", "email": "mail envelope",
    "contact": "mail phone", "call": "phone", "address": "map-pin", "location": "map-pin", "directions": "map",
    "team": "users people", "staff": "users people", "people": "users", "family": "users heart",
    "community": "users", "children": "baby", "kids": "baby", "training": "dumbbell barbell",
    "workout": "dumbbell barbell", "strength": "dumbbell barbell", "fitness": "dumbbell heartbeat",
    "yoga": "lotus person", "massage": "hand spa", "spa": "flower drop", "facial": "smile face",
    "wellness": "heart leaf", "haircut": "scissors", "salon": "scissors", "doctor": "stethoscope",
    "medical": "stethoscope", "health": "heart pulse", "care": "heart hand", "vaccination": "syringe",
    "pharmacy": "pill", "medicine": "pill", "prescription": "pill", "dental": "tooth", "dentist": "tooth",
    "payment": "credit card", "pay": "credit card", "price": "tag", "prices": "tag", "pricing": "tag",
    "discount": "percent", "tax": "receipt", "invoice": "receipt", "bookkeeping": "calculator book",
    "accounting": "calculator", "finance": "chart bank", "legal": "scale gavel", "law": "scale gavel",
    "contract": "file signature", "advice": "chat message", "consultation": "chat message",
    "support": "headset help", "help": "help question", "quality": "badge check star", "award": "award trophy",
    "handmade": "hand heart", "craft": "hammer hand", "organic": "leaf", "fresh": "leaf", "natural": "leaf",
    "local": "map-pin", "growth": "trending up chart", "mail": "envelope", "envelope": "mail",
    "nutrition": "carrot apple leaf", "sourdough": "bread wheat", "espresso": "coffee",
    "check-ups": "stethoscope", "check-up": "stethoscope", "checkup": "stethoscope",
    "security": "shield lock", "secure": "shield lock",
    # Things stats count.
    "clients": "users", "client": "users", "customers": "users", "customer": "users", "members": "users",
    "guests": "users", "patients": "heart pulse", "students": "graduation", "years": "calendar", "year": "calendar",
    "months": "calendar", "days": "calendar", "projects": "briefcase", "project": "briefcase", "orders": "package",
    "products": "package", "reviews": "star", "rating": "star", "ratings": "star", "sites": "globe",
    "countries": "globe", "cities": "map-pin", "replies": "message", "response": "message", "due": "calendar clock",
    "today": "calendar", "cards": "layers", "decks": "layers", "total": "sigma hash", "done": "check",
    "privacy": "shield lock", "safe": "shield", "speed": "zap", "fast": "zap", "quick": "zap",
    "delivery": "truck", "shipping": "truck", "pick-up": "shopping bag", "pickup": "shopping bag",
    "order": "shopping bag", "shop": "shopping bag", "store": "store", "menu": "book utensils",
    "food": "utensils", "restaurant": "utensils", "dinner": "utensils", "breakfast": "coffee egg",
    "bread": "bread wheat", "bakery": "bread wheat croissant", "pastry": "croissant cake", "tea": "leaf cup",
    "wine": "wine", "website": "globe browser", "websites": "globe browser", "web": "globe", "design": "pen",
    "brand": "palette pen", "branding": "palette", "identity": "fingerprint", "photo": "camera",
    "photography": "camera", "video": "video", "travel": "plane", "tour": "map", "hotel": "bed",
    "room": "bed", "event": "calendar star", "music": "music", "learning": "book graduation",
    "course": "book graduation", "class": "graduation", "lesson": "book", "study": "book",
    "time": "clock", "experience": "star", "guarantee": "shield check", "warranty": "shield check",
    "repair": "wrench", "service": "wrench", "cleaning": "sparkles spray", "clean": "sparkles",
    "eco": "leaf recycle", "recycling": "recycle", "energy": "zap", "home": "house", "house": "house",
}  # fmt: skip


def pascal(kebab: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in kebab.split("-"))


def kebab(name: str) -> str:
    """A component name's words in lower case, joined by hyphens (`MapPin` → `map-pin`, `ArrowUp01` →
    `arrow-up-0-1`)."""
    return "-".join(part.lower() for part in re.findall(r"[A-Z][a-z]*|[a-z]+|\d", name))


@lru_cache
def icon_index(path: Path = ICON_INDEX_FILE) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except OSError:
        return {"lucide": {"icons": {}}, "phosphor": {"icons": {}}}


@lru_cache
def icon_words(icon_set: str) -> dict[str, list[str]]:
    """Component name → its words (name, tags, categories), for one set."""
    icons = icon_index()[icon_set]["icons"]
    if icon_set == "lucide":
        return {pascal(name): words for name, words in icons.items()}
    return dict(icons)


@lru_cache
def lucide_files() -> dict[str, str]:
    """Lucide component name → its file name (`lucide-react/icons/<file>`)."""
    return {pascal(name): name for name in icon_index()["lucide"]["icons"]}


@lru_cache
def _lucide_aliases() -> dict[str, str]:
    return dict(icon_index()["lucide"].get("aliases") or {})


def lucide_current(name: str) -> str | None:
    """The current component name of a renamed Lucide icon (`AlertTriangle` → `TriangleAlert`), or None. lucide-react
    still exports the old names, but the index, the icon imports and the checks use the current ones."""
    target = _lucide_aliases().get(kebab(name))
    return pascal(target) if target else None


@lru_cache
def _ranker(icon_set: str) -> tuple[list[str], Bm25]:
    names = sorted(icon_words(icon_set))
    documents = []
    for name in names:
        own = [stem(word) for word in kebab(name).split("-")]
        documents.append(own * NAME_WEIGHT + [stem(w) for word in icon_words(icon_set)[name] for w in word.split()])
    return names, Bm25(documents)


def _query(text: str) -> tuple[list[str], dict[str, float], set[str]]:
    """An intent's words, the objects its words stand for (`OBJECTS`), the weight of its last word, and the whole
    words an icon may be named after (`map-pin` as well as `map` and `pin`)."""
    own = [word for word in re.findall(r"[a-z0-9-]+", text.lower()) if word not in _STOP]
    extra = [w for word in own for w in OBJECTS.get(word, OBJECTS.get(word.rstrip("s"), "")).split()]
    query = [stem(word) for word in [*own, *extra] for word in word.split("-")]
    head = {stem(own[-1].split("-")[-1]): HEAD_WEIGHT} if own else {}
    for word in OBJECTS.get(own[-1], "").split() if own else []:
        for part in word.split("-"):
            head[stem(part)] = HEAD_WEIGHT
    return query, head, set(query) | {stem(word) for word in [*own, *extra]}


def rank_icons(text: str, icon_set: str, limit: int = 5) -> list[tuple[str, float]]:
    """The set's icons that best match some words, best first (name words count double, the last word too)."""
    query, weights, wanted = _query(text)
    names, index = _ranker(icon_set)
    scores = index.scores(query, weights)
    # An icon named exactly after a query word wins over its variants (`Mail` before `MailDot`); among the rest,
    # shorter names (the plain object) come first.
    scores = [
        score * (EXACT_BONUS if stem(kebab(name)) in wanted else 1) / (1 + 0.1 * kebab(name).count("-"))
        for name, score in zip(names, scores, strict=True)
    ]
    ranked = sorted((pair for pair in zip(names, scores, strict=True) if pair[1] > 0), key=lambda p: (-p[1], p[0]))
    return ranked[:limit]


def resolve_icon(ref: str | None, icon_set: str) -> str | None:
    """A reference or intent as a real icon of `icon_set` (`phosphor:Truck`), or None (no icon: the set is `none`,
    the reference is malformed, or nothing matches)."""
    if not ref or icon_set not in SETS or not re.match(ICON_REF, ref):
        return None
    kind, _, value = ref.partition(":")
    if kind == "intent":
        best = rank_icons(value, icon_set, 1)
        return f"{icon_set}:{best[0][0]}" if best else None
    if kind == "lucide":
        value = lucide_current(value) or value
    if value in icon_words(icon_set):
        return f"{icon_set}:{value}"
    best = rank_icons(kebab(value).replace("-", " "), icon_set, 1)
    return f"{icon_set}:{best[0][0]}" if best else None


def closest_icon(name: str, icon_set: str) -> str | None:
    """The set's icon name nearest to an unknown one (spelling), for the validator's hint."""
    names = list(icon_words(icon_set))
    match = difflib.get_close_matches(name, names, n=1, cutoff=0.6)
    return match[0] if match else None


def glyph(name: str, icon_set: str) -> str:
    """The library's mark `name` in a set (Lucide when the set is `none`)."""
    return GLYPHS[name]["phosphor" if icon_set == "phosphor" else "lucide"]
