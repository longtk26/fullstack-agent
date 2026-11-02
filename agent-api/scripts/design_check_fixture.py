"""The section library's design check (Stories 17.7, 20.2): builds the section-library fixture in each theme preset
and runs `scripts/design-check.mjs` on every page at 390 / 768 / 1440 px, light and dark, then checks the measured
rules of `templates/nextjs_overlay/DESIGN_CHECKLIST.md`. Dev tool, not part of generation.

    make design-check-fixture                                  # every preset → .data/shots/design-check/<preset>/
    make design-check-fixture ARGS="--presets minimal editorial --out .data/shots/story20.2"
    make design-check-fixture ARGS="--combos --out .data/shots/story20.3"   # six tone, font and preset combinations
    make design-check-fixture ARGS="--combos --spec ../examples/frontend-specs/shop-dynamic.json \
        --backend ../examples/specs/shop.json"     # a dynamic app on its mock API (Story 20.4)
"""

import argparse
import asyncio
import copy
import json
from pathlib import Path
from typing import Any

from src.modules.shared.domain.frontend_spec import THEME_PRESETS
from src.orchestrator.design_tone import SCALES, apply_tone

from .site_check import REPO, check_site

FIXTURE = REPO / "agent-api" / "tests" / "fixtures" / "frontend-specs" / "section-library.json"
CONCURRENCY = 2
# The measured rules of the design checklist.
MAX_HEADLINE_LINES = 2
MAX_NAV_HEIGHT = 80
MAX_TYPE_SIZES = 5
MAX_FAMILIES = 2
MAX_CHARS_PER_LINE = 75
# Story 20.3: tone (energy, finish, density, weight, seriousness), heading / body font and preset per combination.
COMBOS = {
    "raw-loud": ((5, 1, 3, 5, 4), ("Unbounded", "Archivo"), "minimal"),
    "refined-quiet": ((1, 5, 2, 2, 3), ("Fraunces", "Newsreader"), "editorial"),
    "dense-serious": ((3, 3, 5, 3, 5), ("Familjen Grotesk", "Source Sans 3"), "corporate"),
    "playful-bold": ((4, 4, 2, 4, 1), ("Bricolage Grotesque", "DM Sans"), "playful"),
    "light-airy": ((2, 4, 1, 1, 2), ("Instrument Serif", "Inter"), "minimal"),
    "heavy-refined": ((4, 5, 3, 4, 3), ("Syne", "Inter"), "dashboard"),
}


def variants(fixture: dict[str, Any], presets: list[str], combos: bool) -> dict[str, dict[str, Any]]:
    """The specs to check: the fixture in each preset, or (`--combos`) in each tone combination."""
    out = {}
    if not combos:
        for preset in presets:
            spec = copy.deepcopy(fixture)
            spec["theme"] = {**spec.get("theme", {}), "style": preset}
            out[preset] = spec
        return out
    for name, (levels, (heading, body), preset) in COMBOS.items():
        spec = copy.deepcopy(fixture)
        theme = {**spec.get("theme", {}), "style": preset, "typography": {"headingFont": heading, "bodyFont": body}}
        spec["theme"] = apply_tone(theme, dict(zip(SCALES, levels, strict=True)))
        out[name] = spec
    return out


def failures(view: str, measured: dict[str, Any]) -> list[str]:
    """The checklist rules a page view breaks, as readable lines."""
    found = []
    if (measured.get("h1Lines") or 0) > MAX_HEADLINE_LINES:
        found.append(f"{view}: headline on {measured['h1Lines']} lines")
    if (measured.get("navHeight") or 0) > MAX_NAV_HEIGHT:
        found.append(f"{view}: nav {measured['navHeight']} px")
    if measured.get("ctaAboveFold") is False:
        found.append(f"{view}: primary CTA below the fold")
    if len(measured.get("typeSizes") or []) > MAX_TYPE_SIZES:
        found.append(f"{view}: {len(measured['typeSizes'])} type sizes {measured['typeSizes']}")
    families = [family.strip('"') for family in measured.get("families") or []]
    if len(families) > MAX_FAMILIES:
        found.append(f"{view}: {len(families)} font families {families}")
    missing = [family for family in families if family not in (measured.get("loadedFonts") or [])]
    if missing:
        found.append(f"{view}: fonts not loaded {missing}")
    if (measured.get("maxCharsPerLine") or 0) > MAX_CHARS_PER_LINE:
        found.append(f"{view}: {measured['maxCharsPerLine']} characters per line")
    return found


async def main(args: argparse.Namespace) -> None:
    fixture = json.loads(Path(args.spec).read_text())
    backend = json.loads(Path(args.backend).read_text()) if args.backend else None
    out = Path(args.out)
    gate = asyncio.Semaphore(CONCURRENCY)

    specs = variants(fixture, args.presets, args.combos)

    async def one(name: str) -> tuple[str, dict[str, Any] | None]:
        saved = out / name / "report.json"
        if args.recheck:
            return name, json.loads(saved.read_text()) if saved.is_file() else None
        async with gate:
            print(f"building {name}")
            return name, await check_site(specs[name], out / name, backend=backend)

    summary: dict[str, Any] = {}
    for preset, report in await asyncio.gather(*(one(name) for name in specs)):
        if report is None:
            summary[preset] = {"built": False}
            continue
        broken = [line for view, measured in report.items() for line in failures(view, measured)]
        sizes = sorted({len(measured.get("typeSizes") or []) for measured in report.values()})
        summary[preset] = {"built": True, "views": len(report), "typeSizeCounts": sizes, "failures": broken}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    for preset, result in summary.items():
        state = (
            "build failed" if not result["built"] else f"{result['views']} views, {len(result['failures'])} failures"
        )
        print(f"{preset}: {state}")
        for line in result.get("failures", [])[:20]:
            print(f"  {line}")
    print(f"summary: {out / 'summary.json'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--presets", nargs="+", default=list(THEME_PRESETS), choices=list(THEME_PRESETS))
    parser.add_argument("--spec", default=str(FIXTURE), help="the FrontendSpec to check (default: the fixture)")
    parser.add_argument("--backend", help="the BackendSpec of a dynamic --spec (its API contract and mock data)")
    parser.add_argument("--out", default=str(REPO / ".data" / "shots" / "design-check"))
    parser.add_argument("--combos", action="store_true", help="the six tone combinations instead of the presets")
    parser.add_argument("--recheck", action="store_true", help="re-read the saved reports in --out, build nothing")
    asyncio.run(main(parser.parse_args()))
