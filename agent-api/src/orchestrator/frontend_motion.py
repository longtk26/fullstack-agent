"""Motion presets for rendered sites (Story 20.6). No LLM, no animation library.

A theme's `motion.feel` picks a preset: a spring (stiffness, damping ratio) sampled into a CSS `linear()` easing, a
duration, a travel distance and direction, and the stagger between followers. Two easings come from each spring:
`--motion-ease` for large surfaces (overshoot ≤ 2%) and `--motion-ease-mark` for small marks (≤ 15%). `cut` is
loud and raw: short stepped changes, no travel.

Everything moves only under `html[data-motion="on"]`, which the page's inline script sets when JavaScript runs and the
visitor has not asked for reduced motion (`PageRenderer.tsx`, `MotionRoot.tsx`): without JavaScript or with reduced
motion every element is in its final state. Only transform-like properties (`translate`, `scale`), `opacity` and,
for the image unmask signature, `clip-path` animate; heights stay with the base's accordion.

| Feel | Spring (stiffness, damping) | Duration | Travel | Stagger |
|---|---|---|---|---|
| click | 600, 0.70 | 220 ms | 8 px up | 40 ms |
| slide | 300, 0.85 | 420 ms | 32 px from the left | 60 ms |
| flow | 150, 1.00 | 600 ms | 16 px up | 70 ms |
| drop | 450, 0.60 | 480 ms | 24 px down | 60 ms |
| bounce | 350, 0.40 | 620 ms | 20 px up | 70 ms |
| float | 90, 0.90 | 800 ms | 12 px up | 80 ms |
| cut | stepped | 120 ms | none | 40 ms |

The hero's entrance uses `--motion-enter`: the feel's duration, shortened so headline, text, actions and image (three
staggers apart) are all in place within 600 ms.
"""

import math
from typing import Any

# feel → (stiffness, damping ratio, duration ms, x px, y px, stagger ms)
FEELS: dict[str, tuple[float, float, int, int, int, int]] = {
    "click": (600, 0.70, 220, 0, 8, 40),
    "slide": (300, 0.85, 420, -32, 0, 60),
    "flow": (150, 1.00, 600, 0, 16, 70),
    "drop": (450, 0.60, 480, 0, -24, 60),
    "bounce": (350, 0.40, 620, 0, 20, 70),
    "float": (90, 0.90, 800, 0, 12, 80),
    "cut": (0, 1.0, 120, 0, 0, 40),
}
SIGNATURES = ("countUp", "headlineRise", "imageUnmask", "indicator")
SURFACE_OVERSHOOT = 0.02
MARK_OVERSHOOT = 0.15
SAMPLES = 24
COUNT_MS = 900
ENTRANCE_MS = 600  # the hero's whole entrance, its last part (the image, three staggers in) included
SIGNATURE_COUNT_MS = 1600
PRESS_SCALE = 0.97


def damping_for(overshoot: float) -> float:
    """The damping ratio whose spring overshoots by `overshoot` (e^(−ζπ/√(1−ζ²)) = overshoot)."""
    log = math.log(overshoot)
    return -log / math.sqrt(math.pi**2 + log**2)


def spring(stiffness: float, ratio: float, t: float) -> float:
    """Position of a unit spring (mass 1) released from 0 towards 1, at time `t` seconds."""
    omega = math.sqrt(stiffness)
    if ratio >= 1:  # critically damped (or more): no overshoot
        return 1 - math.exp(-omega * t) * (1 + omega * t)
    damped = omega * math.sqrt(1 - ratio**2)
    decay = math.exp(-ratio * omega * t)
    return 1 - decay * (math.cos(damped * t) + ratio * omega / damped * math.sin(damped * t))


def settle_time(stiffness: float, ratio: float, tolerance: float = 0.002) -> float:
    """The last moment the spring is more than `tolerance` away from 1 (searched in 1 ms steps up to 5 s)."""
    last = 0.0
    for step in range(1, 5000):
        t = step / 1000
        if abs(1 - spring(stiffness, ratio, t)) > tolerance:
            last = t
    return last + 0.001


def linear_easing(stiffness: float, ratio: float, samples: int = SAMPLES) -> list[float]:
    """The spring sampled evenly over its settle time, ending exactly at 1 (CSS `linear()` points)."""
    end = settle_time(stiffness, ratio)
    points = [round(spring(stiffness, ratio, end * i / samples), 4) for i in range(samples + 1)]
    points[0], points[-1] = 0.0, 1.0
    return points


def css_linear(points: list[float]) -> str:
    return "linear(" + ", ".join(f"{point:g}" for point in points) + ")"


def motion_vars(motion: dict[str, Any]) -> list[str]:
    """The `:root` variables of a feel."""
    stiffness, ratio, duration, x, y, stagger = FEELS[motion["feel"]]
    count = SIGNATURE_COUNT_MS if motion.get("signature") == "countUp" else COUNT_MS
    if motion["feel"] == "cut":
        surface = mark = "steps(2, jump-end)"
    else:
        surface = css_linear(linear_easing(stiffness, max(ratio, damping_for(SURFACE_OVERSHOOT))))
        mark = css_linear(linear_easing(stiffness, max(ratio, damping_for(MARK_OVERSHOOT))))
    return [
        f"  --motion-duration: {duration}ms;",
        f"  --motion-enter: {min(duration, ENTRANCE_MS - 3 * stagger)}ms;",
        f"  --motion-ease: {surface};",
        f"  --motion-ease-mark: {mark};",
        f"  --motion-x: {x}px;",
        f"  --motion-y: {y}px;",
        f"  --motion-stagger: {stagger}ms;",
        f"  --motion-count: {count}ms;",
    ]


# Content that a section's reveal moves: headings, cards, list items, figures, quotes, images, tables.
REVEALED = "h2, [data-slot='card'], li, dt, dd, figure, blockquote, img, table"
SECTION = "html[data-motion='on'] [data-bga-section]:not([data-bga-component='Hero'])"
MOTION_CSS = f"""/* Story 20.6: motion, only once the page's script set data-motion="on" (JavaScript runs and the
   visitor has not asked for reduced motion). Without it every element is in its final state. */
@keyframes bga-enter {{
  from {{
    opacity: 0;
    translate: var(--motion-x) var(--motion-y);
  }}
}}
html[data-motion='on'] [data-motion-part] {{
  animation: bga-enter var(--motion-enter) var(--motion-ease) both;
}}
html[data-motion='on'] [data-motion-part='text'] {{
  animation-delay: var(--motion-stagger);
}}
html[data-motion='on'] [data-motion-part='action'] {{
  animation-delay: calc(var(--motion-stagger) * 2);
}}
html[data-motion='on'] [data-bga-component='Hero'] [data-bga-asset] {{
  animation: bga-enter var(--motion-enter) var(--motion-ease) calc(var(--motion-stagger) * 3) both;
}}
html[data-motion='on'] [data-slot='button']:active {{
  scale: {PRESS_SCALE};
}}
html[data-motion='on'] [data-slot='tabs-trigger']::after {{
  scale: 0 1;
  transition: opacity var(--motion-duration) var(--motion-ease), scale var(--motion-duration) var(--motion-ease);
}}
html[data-motion='on'] [data-slot='tabs-trigger'][data-active]::after {{
  scale: 1 1;
}}
{SECTION} :is({REVEALED}) {{
  transition:
    opacity var(--motion-duration) var(--motion-ease),
    translate var(--motion-duration) var(--motion-ease-mark),
    scale var(--motion-duration) var(--motion-ease);
}}
{SECTION}:not([data-revealed]) :is({REVEALED}) {{
  opacity: 0;
  translate: var(--motion-x) var(--motion-y);
}}
{SECTION}:not([data-revealed]) img {{
  scale: 1.08;
}}
""" + "".join(
    f"{SECTION} :is([data-slot='card'], li, figure):nth-child({n}) {{\n"
    f"  transition-delay: calc(var(--motion-stagger) * {min(n - 1, 5)});\n}}\n"
    for n in range(2, 8)
)
SIGNATURE_CSS = {
    "headlineRise": """@keyframes bga-rise {
  from {
    clip-path: inset(0 0 100% 0);
    translate: 0 0.35em;
  }
  to {
    clip-path: inset(0 0 -0.25em 0);
  }
}
html[data-motion='on'] [data-bga-component='Hero'] h1[data-motion-part] {
  animation: bga-rise calc(var(--motion-duration) * 1.4) var(--motion-ease) both;
}
""",
    "imageUnmask": """@keyframes bga-unmask {
  from {
    clip-path: inset(0 100% 0 0);
    scale: 1.08;
  }
  to {
    clip-path: inset(0);
  }
}
html[data-motion='on'] [data-bga-component='Hero'] [data-bga-asset] {
  animation: bga-unmask calc(var(--motion-duration) * 1.6) var(--motion-ease) calc(var(--motion-stagger) * 3) both;
}
""",
    "indicator": """html[data-motion='on'] header nav a {
  background: linear-gradient(currentColor, currentColor) no-repeat 0 100% / 0 2px;
  transition: background-size var(--motion-duration) var(--motion-ease);
}
html[data-motion='on'] header nav a:is(:hover, :focus-visible, [aria-current='page']) {
  background-size: 100% 2px;
}
""",
    "countUp": "",
}


def motion_css(motion: dict[str, Any] | None) -> str:
    """The motion rules for `globals.css`, or nothing for a still site."""
    if not motion or motion.get("feel", "none") == "none":
        return ""
    return MOTION_CSS + SIGNATURE_CSS.get(motion.get("signature") or "none", "")
