"""The app kit's design check (Story 22.4): plans an app of the dynamic app flow (outline → screens, no engine),
builds it and runs `scripts/design-check.mjs` on its screens at 375 and 1440 px, light and dark, on the mock API.
Parameterised routes take the first fixture record. Dev tool, not part of generation.

    make design-check-app                                    # flashcards → .data/shots/design-check-app/flashcards/
    make design-check-app ARGS="--app two-entity:project-tracker --out .data/shots/story22.4"
"""

import argparse
import asyncio
import json
import re
from pathlib import Path
from typing import Any

from .site_check import REPO, check_site

EXAMPLES = REPO / "examples"


def app_spec(backend_name: str, outline_name: str | None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    from src.modules.shared.domain.backend_spec import validate_spec_data
    from src.orchestrator.backend.planner import build_plan
    from src.orchestrator.frontend.app.outline import complete_outline
    from src.orchestrator.frontend.app.screens import app_frontend_spec, ensure_aggregates
    from src.orchestrator.integration.contract import build_contract

    backend = validate_spec_data(json.loads((EXAMPLES / "specs" / f"{backend_name}.json").read_text())).normalized
    raw = json.loads((EXAMPLES / "app-outlines" / f"{outline_name}.json").read_text()) if outline_name else {}
    outline, _ = complete_outline(raw, backend, build_contract(backend, build_plan(backend)))
    backend, outline, _ = ensure_aggregates(backend, outline)
    contract = build_contract(backend, build_plan(backend))
    theme = {"style": "dashboard", "colorScheme": "light-dark", "density": "comfortable"}
    return app_frontend_spec(backend, outline, theme, contract).spec, backend, contract


def screen_routes(spec: dict[str, Any], contract: dict[str, Any]) -> list[str]:
    """Every screen, `[id]` filled with the first fixture record of the entity the route's first segment names."""
    fixtures = (contract.get("x-bga") or {}).get("fixtures") or {}
    entities = (spec.get("app") or {}).get("entities") or {}
    from src.modules.shared.domain.backend_spec.naming import pluralize, to_kebab

    by_slug = {to_kebab(pluralize(name)): name for name in entities}
    routes = []
    for page in spec["pages"]:
        route = page["route"]
        if "[id]" in route:
            entity = by_slug.get(route.strip("/").split("/")[0])
            rows = fixtures.get(entity or "") or []
            if not rows:
                continue
            route = re.sub(r"\[id\]", str(rows[0].get("id")), route)
        routes.append(route)
    return routes


async def main(args: argparse.Namespace) -> None:
    for item in args.app:
        backend_name, _, outline_name = item.partition(":")
        spec, backend, contract = app_spec(backend_name, outline_name or None)
        out = Path(args.out) / backend_name
        print(f"building {backend_name}")
        report = await check_site(
            spec, out, routes=screen_routes(spec, contract), widths=args.widths, schemes=args.schemes, backend=backend
        )
        print(f"{backend_name}: {'failed' if report is None else f'{len(report)} views'} → {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--app", nargs="+", default=["flashcards:flashcards"], help="<BackendSpec example>[:<outline>]")
    parser.add_argument("--out", default=str(REPO / ".data" / "shots" / "design-check-app"))
    parser.add_argument("--widths", default="375,1440")
    parser.add_argument("--schemes", default="light,dark")
    asyncio.run(main(parser.parse_args()))
