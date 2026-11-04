"""TESTING / DEMO ONLY (docs/development/test-doubles.md). Direction cards for the fake engine's drafts (Story 20.4).

Real engines write their own cards from the requirement. The fake draws three from a curated library
(`design_data/concepts.json`) with the draft's seed: concepts whose keywords the requirement mentions weigh more, and
a card is only taken when it differs from the ones already drawn (the difference test), so fake drafts show varied,
reproducible directions. Each card composes the home page from the copied example's sections (Story 20.9). Items that
can show an icon get an intent from their title (Story 20.5); icons and motion come from each card's tone.
"""

import json
import random
from functools import lru_cache
from pathlib import Path
from typing import Any

CONCEPTS = Path(__file__).resolve().parents[2] / "design_data" / "concepts.json"
MATCH_WEIGHT = 4
# Sections a card may leave off its home page; a trailing CallToAction or ContactInfo stays last.
OPTIONAL = frozenset({"Testimonials", "Stats", "Faq", "Pricing", "Gallery"})
CLOSING = frozenset({"CallToAction", "ContactInfo"})


@lru_cache
def concepts() -> list[dict[str, Any]]:
    return json.loads(CONCEPTS.read_text())["concepts"]


def _fields(card: dict[str, Any]) -> dict[str, str]:
    from src.orchestrator.drafting.design_diversity import hue_family

    return {
        "hero": card["heroLayout"],
        "headingFont": card["fonts"]["heading"],
        "hueFamily": hue_family(card["colors"]["primary"]),
        "keyVisual": card["keyVisual"],
    }


def _differs(card: dict[str, Any], picked: list[dict[str, Any]]) -> bool:
    from src.orchestrator.drafting.design_diversity import shared_fields

    if any(card["heroLayout"] == other["heroLayout"] for other in picked):
        return False
    return all(len(shared_fields(_fields(card), _fields(other))) <= 1 for other in picked)


def homes(sections: list[dict[str, Any]], count: int) -> list[list[str]]:
    """Home page compositions (section ids): the drafted order, then the middle sections in another order, then one
    optional section left out (or the middle reversed)."""
    ids = [s["id"] for s in sections if s.get("id")]
    if not ids:
        return [[] for _ in range(count)]
    by_id = {s["id"]: s.get("component") for s in sections if s.get("id")}
    head = [ids[0]] if by_id[ids[0]] == "Hero" else []
    tail = [ids[-1]] if len(ids) > 1 and by_id[ids[-1]] in CLOSING else []
    middle = [i for i in ids if i not in head and i not in tail]
    out = [ids]
    out.append(head + middle[1:] + middle[:1] + tail)
    optional = [i for i in middle if by_id[i] in OPTIONAL]
    if optional and len(middle) > 1:
        out.append(head + [i for i in middle if i != optional[-1]] + tail)
    else:
        out.append(head + list(reversed(middle)) + tail)
    return out[:count]


def fake_cards(requirement: str, seed: int, home_sections: list[dict[str, Any]], count: int = 3) -> list[dict]:
    """`count` cards that pass the difference test among themselves, the same for the same seed."""
    text = requirement.lower()
    rng = random.Random(seed)

    def key(concept: dict[str, Any]) -> float:
        weight = MATCH_WEIGHT if any(word in text for word in concept["keywords"]) else 1
        return rng.random() ** (1 / weight)  # weighted shuffle: larger keys first

    ordered = sorted(concepts(), key=key, reverse=True)
    picked: list[dict[str, Any]] = []
    for concept in ordered:
        if _differs(concept, picked):
            picked.append(concept)
        if len(picked) == count:
            break
    compositions = homes(home_sections, count)
    cards = []
    for position, concept in enumerate(picked):
        card = {k: v for k, v in concept.items() if k != "keywords"}
        card["evidence"] = "Fake engine: drawn from the concept library"
        card["fit"] = position + 1
        if compositions[position]:
            card["home"] = compositions[position]
        cards.append(card)
    return cards


ICON_SECTIONS = {"Features": "title", "Stats": "label", "Pricing": "name"}


def with_icon_intents(spec: dict[str, Any]) -> dict[str, Any]:
    """Story 20.5: the copied example with an icon intent on every Features, Stats and Pricing item (its title,
    label or name), in the section content and in the collections those sections show, as a drafter would."""

    def mark(items: Any, key: str) -> None:
        for item in items if isinstance(items, list) else []:
            if isinstance(item, dict) and isinstance(item.get(key), str) and "icon" not in item:
                item["icon"] = f"intent:{item[key][:60]}"

    collections = {c.get("collection"): c.get("records") for c in spec.get("content") or [] if isinstance(c, dict)}

    def visit(sections: Any) -> None:
        for section in sections if isinstance(sections, list) else []:
            key = ICON_SECTIONS.get(section.get("component")) if isinstance(section, dict) else None
            if key:
                mark((section.get("content") or {}).get("items"), key)
                mark(collections.get((section.get("data") or {}).get("collection")), key)
            if isinstance(section, dict):
                visit(section.get("children"))

    for page in spec.get("pages") or []:
        visit(page.get("sections"))
    return spec
