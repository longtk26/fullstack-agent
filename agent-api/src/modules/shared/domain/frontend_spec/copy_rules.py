"""Stock phrases in headings and calls to action (Story 20.9).

Phrases every generated site uses ("Explore …", "Why choose us") make sites feel like one template. The drafting
prompt lists them as phrases to avoid, the validator warns `FE_DESIGN_RULE` where one is left, and drafting runs one
repair round for them. Only the copy a visitor notices first is checked: headings, titles, eyebrows and button
labels.
"""

import re
from collections.abc import Iterator
from typing import Any

# (pattern on the whole line, lower case, as shown to the engine)
STOCK_PHRASES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(rf"^{word}\b"), f"{word.capitalize()} …")
    for word in ("explore", "discover", "unlock", "elevate", "unleash", "experience the", "welcome to")
] + [
    (re.compile(rf"^{phrase}[.!]?$"), phrase.capitalize())
    for phrase in (
        "why choose us",
        "our services",
        "get started",
        "get started today",
        "learn more",
        "read more",
        "find out more",
        "contact us today",
        "join us today",
    )
]
# Content keys that hold the first-noticed copy; the walk goes into these and into call-to-action objects.
COPY_KEYS = frozenset({"heading", "title", "eyebrow", "label"})
CTA_KEYS = frozenset({"cta", "secondaryCta", "actions", "primaryCta"})


def stock_phrase(text: str) -> str | None:
    """The stock phrase a heading or label is built on, or None."""
    line = re.sub(r"\s+", " ", text).strip().lower()
    return next((label for pattern, label in STOCK_PHRASES if pattern.search(line)), None)


def stock_copy(content: Any, path: str) -> Iterator[tuple[str, str, str]]:
    """(path, text, phrase) for each stock phrase in a section's content: its own headings and labels, those of its
    calls to action and those of its items."""
    if not isinstance(content, dict):
        return
    for key, value in content.items():
        if key in COPY_KEYS and isinstance(value, str):
            phrase = stock_phrase(value)
            if phrase:
                yield f"{path}/{key}", value, phrase
        elif key in CTA_KEYS or key == "items":
            children = value if isinstance(value, list) else [value]
            for index, child in enumerate(children):
                child_path = f"{path}/{key}/{index}" if isinstance(value, list) else f"{path}/{key}"
                yield from stock_copy(child, child_path)


def phrase_list() -> str:
    """The phrases for the drafting prompt, one line."""
    return ", ".join(f'"{label}"' for _, label in STOCK_PHRASES)
