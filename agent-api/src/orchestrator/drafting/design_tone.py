"""Tone → theme tokens (Story 20.3). No LLM.

A direction's feel is five scales from 1 to 5 (oil-ui's method, docs/research/design-diversity.md): **energy**
(quiet ↔ loud), **finish** (raw ↔ refined), **density** (sparse ↔ dense), **weight** (light ↔ heavy) and
**seriousness** (playful ↔ solemn). The drafting engine judges the tone from the requirement (Story 20.4); this module
turns it into the theme tokens the renderer draws, so the same tone always looks the same and every value stays
inside the design checklist.

| Token | Decided by |
|---|---|
| `colorArea` | energy: 1–2 minimal (colour on buttons), 3 block (one anchor section), 4–5 bold (coloured hero) |
| `typography.ratio` | energy: 1 tight, 2–3 default, 4–5 dramatic (bigger display steps) |
| `radius` | finish 1 (raw): none; otherwise seriousness: 1–2 lg, 3 md, 4–5 sm |
| `surface` | finish 1–2: outline (hard lines); 3: outline; 4–5: raised when weight ≥ 3, else flat |
| `density` | density: 4–5 compact, otherwise comfortable |
| `typography.headingWeight` | weight: 1 → 400, 2 → 500, 3 → 600, 4–5 → 700 |
| `typography.headingCase` | upper when seriousness ≥ 4 and energy ≥ 4 (loud and solemn), else normal |
| `typography.tracking` | wide with upper case; tight when weight ≥ 4 or the ratio is dramatic; otherwise normal |

The table is the contract; `tests/test_design_tone.py` checks it case by case.

Icons (Story 20.5) and motion (Story 20.6), first matching row:

| Icons (`theme.icons`) | When |
|---|---|
| none | finish 1 (raw), or seriousness 5 with energy ≤ 2 (quiet editorial): lists keep their numbers |
| lucide thin / light, plain | weight 1 / 2 with finish ≥ 4 (light and refined) |
| phosphor duotone, tile | weight ≥ 4 and seriousness ≤ 2 (heavy and playful) |
| phosphor fill (energy ≥ 4) or bold, plain | weight ≥ 4 |
| phosphor regular, tile | seriousness ≤ 2 |
| lucide regular, plain | otherwise |

| Motion feel (`theme.motion.feel`) | When |
|---|---|
| none | energy 1 with weight ≤ 2 (very quiet) |
| cut | finish 1 with energy ≥ 4 (raw and loud) |
| bounce | energy ≥ 4 with seriousness ≤ 2 |
| click (energy ≥ 4) or drop | weight ≥ 4 |
| float (energy ≤ 2) or flow | weight ≤ 2 |
| slide | otherwise |
"""

from typing import Any

SCALES = ("energy", "finish", "density", "weight", "seriousness")
NEUTRAL = 3


def _level(tone: dict[str, Any], scale: str) -> int:
    """A scale's value clamped to 1–5; missing or unreadable values count as the neutral middle."""
    try:
        return min(5, max(1, int(tone.get(scale, NEUTRAL))))
    except (TypeError, ValueError):
        return NEUTRAL


def normalize_tone(tone: dict[str, Any] | None) -> dict[str, int]:
    return {scale: _level(tone or {}, scale) for scale in SCALES}


def tone_tokens(tone: dict[str, Any] | None) -> dict[str, Any]:
    """The theme tokens for a tone: `colorArea`, `surface`, `radius`, `density` and the typography tokens (merge
    them into a FrontendSpec theme; fonts and colours are chosen separately)."""
    t = normalize_tone(tone)
    energy, finish, density, weight, serious = (t[scale] for scale in SCALES)
    ratio = "tight" if energy == 1 else "dramatic" if energy >= 4 else "default"
    upper = serious >= 4 and energy >= 4
    if upper:
        tracking = "wide"
    elif weight >= 4 or ratio == "dramatic":
        tracking = "tight"
    else:
        tracking = "normal"
    if finish == 1:
        radius = "none"
    else:
        radius = "lg" if serious <= 2 else "md" if serious == 3 else "sm"
    if finish >= 4:
        surface = "raised" if weight >= 3 else "flat"
    else:
        surface = "outline"
    return {
        "colorArea": "minimal" if energy <= 2 else "block" if energy == 3 else "bold",
        "surface": surface,
        "radius": radius,
        "density": "compact" if density >= 4 else "comfortable",
        "typography": {
            "headingWeight": {1: 400, 2: 500, 3: 600}.get(weight, 700),
            "headingCase": "upper" if upper else "normal",
            "tracking": tracking,
            "ratio": ratio,
        },
    }


def apply_tone(theme: dict[str, Any], tone: dict[str, Any] | None) -> dict[str, Any]:
    """A copy of a FrontendSpec theme with the tone's tokens; its fonts, colours and other fields are kept."""
    tokens = tone_tokens(tone)
    typography = {**(theme.get("typography") or {}), **tokens.pop("typography")}
    return {**theme, **tokens, "typography": typography}


def icon_style(tone: dict[str, Any] | None) -> dict[str, str]:
    """`theme.icons` for a tone (the table above)."""
    t = normalize_tone(tone)
    energy, finish, weight, serious = t["energy"], t["finish"], t["weight"], t["seriousness"]
    if finish == 1 or (serious == 5 and energy <= 2):
        return {"set": "none", "weight": "regular", "treatment": "plain"}
    if weight <= 2 and finish >= 4:
        return {"set": "lucide", "weight": "thin" if weight == 1 else "light", "treatment": "plain"}
    if weight >= 4 and serious <= 2:
        return {"set": "phosphor", "weight": "duotone", "treatment": "tile"}
    if weight >= 4:
        return {"set": "phosphor", "weight": "fill" if energy >= 4 else "bold", "treatment": "plain"}
    if serious <= 2:
        return {"set": "phosphor", "weight": "regular", "treatment": "tile"}
    return {"set": "lucide", "weight": "regular", "treatment": "plain"}


def motion_feel(tone: dict[str, Any] | None) -> str:
    """`theme.motion.feel` for a tone (the table above)."""
    t = normalize_tone(tone)
    energy, finish, weight, serious = t["energy"], t["finish"], t["weight"], t["seriousness"]
    if energy == 1 and weight <= 2:
        return "none"
    if finish == 1 and energy >= 4:
        return "cut"
    if energy >= 4 and serious <= 2:
        return "bounce"
    if weight >= 4:
        return "click" if energy >= 4 else "drop"
    if weight <= 2:
        return "float" if energy <= 2 else "flow"
    return "slide"
