"""The design diversity report (Story 20.1): drafts the golden requirement set and measures how different the designs
are, within a draft, across drafts of one brief and across similar businesses. Dev tool, not part of generation.

    make design-diversity                          # fake engine, field measures only
    make design-diversity ARGS="--screenshots"     # + build each direction and compare first screens (Docker)
    make design-diversity ARGS="--engine claude-code"   # a real engine: costs money, only with the user's yes

Drafts run in-process through the worker's `DraftRunner` against the dev database (rows are deleted afterwards).
AI photos are always off here (`IMAGE_PROVIDER=none`), so a run never calls the image API. Output:
`.data/reports/design-diversity/<timestamp>/report.json` + `report.md` (+ `shots/`).
"""

import argparse
import asyncio
import json
import shutil
import statistics
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlmodel import Session, delete, select

from src.configs import config
from src.engines import EngineRegistry, PromptLibrary
from src.engines.fake_engine import FakeEngine, demo_scenario
from src.engines.registry import build_engine_registry
from src.libs.database import db_session_manager
from src.modules.shared.infrastructure.models import SpecDraftModel, UserModel
from src.orchestrator import design_diversity as dd
from src.orchestrator.design_direction import apply_direction, design_data, home_order, rank_products
from src.orchestrator.drafting import DraftRunner
from src.orchestrator.store import JobStore

from .site_check import check_site

REPO = Path(__file__).resolve().parents[2]
EXAMPLES = REPO / "examples"
GOLDEN = EXAMPLES / "requirements" / "diversity"
REPORTS = REPO / ".data" / "reports" / "design-diversity"
SHOT_CONCURRENCY = 2


# -- drafting ----------------------------------------------------------------------------------------------------------


def _owner() -> uuid.UUID:
    with Session(db_session_manager.engine) as session:
        user = session.exec(select(UserModel).order_by(UserModel.created_at)).first()
    if user is None:
        sys.exit("No user in the database: start the stack once (`make up`) so the seeded users exist.")
    return user.id


def _registry(engine: str, root: Path) -> EngineRegistry:
    if engine == "fake":
        return EngineRegistry([FakeEngine(allowed_root=root, scenario=demo_scenario(0))], default="fake")
    return build_engine_registry()


async def draft(runner: DraftRunner, owner: uuid.UUID, engine: str, requirement: str) -> dict[str, Any]:
    """One static draft through the worker's runner; returns the stored draft as JSON."""
    row = SpecDraftModel(owner_id=owner, mode="static", requirement_text=requirement, engine=engine)
    with Session(db_session_manager.engine) as session:
        session.add(row)
        session.commit()
        draft_id = row.id
    await runner.run(str(draft_id))
    stored = JobStore().draft(draft_id)
    return stored.model_dump(mode="json") if stored else {"id": str(draft_id), "status": "MISSING"}


def direction_specs(stored: dict[str, Any]) -> list[dict[str, Any]]:
    """The draft's FrontendSpec with each of its directions applied (what switching in the Design panel gives)."""
    spec, design = stored.get("frontend_spec"), stored.get("design") or {}
    if not spec:
        return []
    return [apply_direction(spec, direction) for direction in design.get("directions") or []] or [spec]


def category_default(requirement: str) -> list[str]:
    """The home order of the category's usual landing pattern (the best matching UI UX Pro Max product)."""
    data = design_data()
    ranked = rank_products(requirement, data)
    product = data.products[ranked[0][0] if ranked else 0]
    return home_order(product["Landing Page Pattern"])[0]


def _seconds(stored: dict[str, Any]) -> float | None:
    if not stored.get("started_at") or not stored.get("finished_at"):
        return None
    started = datetime.fromisoformat(stored["started_at"])
    return round((datetime.fromisoformat(stored["finished_at"]) - started).total_seconds(), 2)


# -- screenshots -------------------------------------------------------------------------------------------------------


async def screenshot(spec: dict[str, Any], target: Path) -> Path | None:
    """The home page at 1440 px, light, reduced motion, built by the renderer; None when the build failed."""
    shots = target.parent / f"{target.name}-shots"
    report = await check_site(spec, shots, routes=["/"], widths="1440", schemes="light")
    if report is None:
        return None
    kept = target.parent / f"{target.name}.png"
    shutil.move(shots / "home-1440-light.png", kept)
    shutil.rmtree(shots, ignore_errors=True)
    return kept


# -- report ------------------------------------------------------------------------------------------------------------


def measure_draft(stored: dict[str, Any], requirement: str) -> dict[str, Any]:
    specs = direction_specs(stored)
    fields = [dd.visual_fields(spec) for spec in specs]
    homes = [dd.home_sections(spec) for spec in specs]
    default = category_default(requirement)
    return {
        "draftId": stored.get("id"),
        "status": stored.get("status"),
        "seconds": _seconds(stored),
        "modelCalls": (stored.get("usage") or {}).get("modelCalls"),
        "directions": [{**item, "home": home} for item, home in zip(fields, homes, strict=True)],
        "categoryDefault": default,
        "offDefault": [dd.off_default(home, default) for home in homes],
        "differenceProblems": dd.difference_problems(fields, homes, default),
        "spec": stored.get("frontend_spec"),
        "directionSpecs": specs,
    }


def summarise(results: dict[str, list[dict[str, Any]]], manifest: dict[str, Any]) -> dict[str, Any]:
    drafts = [item for runs in results.values() for item in runs if item["directions"]]
    same = results.get(manifest["sameBrief"], [])
    pairs = []
    for first, second in manifest["pairs"]:
        a, b = results.get(first, []), results.get(second, [])
        if a and b and a[0]["directions"] and b[0]["directions"]:
            distance = dd.pair_distance(a[0]["directions"][0], b[0]["directions"][0])
            pairs.append({"pair": [first, second], "distance": distance})
    firsts = {name: runs[0]["spec"] for name, runs in results.items() if runs and runs[0].get("spec")}
    names = sorted(firsts)
    composition = [
        dd.jaccard(set(dd.home_sections(firsts[a])), set(dd.home_sections(firsts[b])))
        for i, a in enumerate(names)
        for b in names[i + 1 :]
    ]
    seconds = [item["seconds"] for item in drafts if item["seconds"] is not None]
    return {
        "drafts": len(drafts),
        "passDifferenceTest": round(sum(not item["differenceProblems"] for item in drafts) / len(drafts), 3)
        if drafts
        else None,
        "sameBriefDistinctTriples": dd.distinct_triples(d for item in same for d in item["directions"]),
        "sameBriefDirections": sum(len(item["directions"]) for item in same),
        "pairs": pairs,
        "pairsMeetingTarget": sum(1 for pair in pairs if pair["distance"] >= 2),
        "tropeShare": round(sum(not any(item["offDefault"]) for item in drafts) / len(drafts), 3) if drafts else None,
        "sectionFrequency": dd.section_frequency(list(firsts.values())),
        "homeCompositionJaccard": round(statistics.mean(composition), 3) if composition else None,
        "repeatedCopy": dd.repeated_copy(list(firsts.values())),
        "draftSeconds": {"mean": round(statistics.mean(seconds), 2), "max": max(seconds)} if seconds else None,
    }


def markdown(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        f"# Design diversity report ({report['createdAt']})",
        "",
        f"Engine `{report['engine']}`, {s['drafts']} drafts, {report['sameBriefRuns']} runs of the same brief.",
        "",
        "| Measure | Value |",
        "|---|---|",
        f"| Drafts passing the difference test | {s['passDifferenceTest']} |",
        f"| Same brief: distinct (hero, heading font, hue) | {s['sameBriefDistinctTriples']} of "
        f"{s['sameBriefDirections']} directions |",
        f"| Paired domains with ≥ 2 differing fields | {s['pairsMeetingTarget']} of {len(s['pairs'])} |",
        f"| Drafts whose 3 directions all follow the category default | {s['tropeShare']} |",
        f"| Mean home-composition Jaccard (different requirements) | {s['homeCompositionJaccard']} |",
        f"| Repeated headings / CTA labels | {len(s['repeatedCopy'])} |",
        f"| Draft time (s) | {s['draftSeconds']} |",
    ]
    if "similarity" in report:
        sim = report["similarity"]
        lines.append(f"| First-screen similarity within a draft (mean / max) | {sim['mean']} / {sim['max']} |")
    lines += ["", "## Directions", "", "| Requirement | Run | # | Hero | Heading font | Hue | Key visual | Home |"]
    lines.append("|---|---|---|---|---|---|---|---|")
    for name, runs in report["results"].items():
        for run_index, item in enumerate(runs):
            for index, direction in enumerate(item["directions"]):
                lines.append(
                    f"| {name} | {run_index + 1} | {index + 1} | {direction['hero']} | {direction['headingFont']} | "
                    f"{direction['hueFamily']} | {direction['keyVisual']} | {' → '.join(direction['home'])} |"
                )
    lines += ["", "## Section frequency", ""]
    lines += [f"- {name}: {share}" for name, share in s["sectionFrequency"].items()]
    if s["repeatedCopy"]:
        lines += ["", "## Repeated headings and CTA labels", ""]
        lines += [f"- “{line}” in {count} sites" for line, count in s["repeatedCopy"].items()]
    problems = [
        (n, i, p) for n, runs in report["results"].items() for i, r in enumerate(runs) for p in r["differenceProblems"]
    ]
    if problems:
        lines += ["", "## Difference test problems", ""]
        lines += [f"- {name} run {index + 1}: {problem}" for name, index, problem in problems]
    return "\n".join(lines) + "\n"


async def main(args: argparse.Namespace) -> None:
    config.image_provider = "none"  # never call the image API from the report
    manifest = json.loads((GOLDEN / "manifest.json").read_text())
    out = REPORTS / datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    work = out / "drafts"
    work.mkdir(parents=True)
    owner = _owner()
    runner = DraftRunner(_registry(args.engine, work), PromptLibrary(), JobStore(), work, "design-report", EXAMPLES)
    results: dict[str, list[dict[str, Any]]] = {}
    created: list[str] = []
    try:
        for name in manifest["requirements"]:
            requirement = (GOLDEN / f"{name}.md").read_text()
            runs = args.runs if name == manifest["sameBrief"] else 1
            for run in range(runs):
                stored = await draft(runner, owner, args.engine, requirement)
                created.append(str(stored["id"]))
                results.setdefault(name, []).append(measure_draft(stored, requirement))
                print(f"{name} #{run + 1}: {stored.get('status')}")
    finally:
        with Session(db_session_manager.engine) as session:
            session.exec(delete(SpecDraftModel).where(SpecDraftModel.id.in_([uuid.UUID(i) for i in created])))
            session.commit()
        shutil.rmtree(work, ignore_errors=True)
    report: dict[str, Any] = {
        "createdAt": datetime.now(UTC).isoformat(timespec="seconds"),
        "engine": args.engine,
        "sameBriefRuns": args.runs,
        "summary": summarise(results, manifest),
        "results": results,
    }
    if args.screenshots:
        report["similarity"] = await similarity(results, out / "shots")
    for runs in results.values():
        for item in runs:
            item.pop("spec", None)
            item.pop("directionSpecs", None)
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (out / "report.md").write_text(markdown(report))
    print(f"report: {out / 'report.md'}")


async def similarity(results: dict[str, list[dict[str, Any]]], shots: Path) -> dict[str, Any]:
    """First-screen similarity of the three directions of each requirement's first draft."""
    shots.mkdir(parents=True, exist_ok=True)
    gate = asyncio.Semaphore(SHOT_CONCURRENCY)
    per_draft: dict[str, list[float]] = {}

    async def shoot(name: str, index: int, spec: dict[str, Any]) -> tuple[str, int, Path | None]:
        async with gate:
            print(f"building {name} direction {index + 1}")
            return name, index, await screenshot(spec, shots / f"{name}-{index + 1}-build")

    jobs = [
        shoot(name, index, spec)
        for name, runs in results.items()
        if runs
        for index, spec in enumerate(runs[0]["directionSpecs"])
    ]
    images: dict[str, dict[int, Path]] = {}
    for name, index, path in await asyncio.gather(*jobs):
        if path is not None:
            kept = shots / f"{name}-{index + 1}.png"
            path.rename(kept)
            images.setdefault(name, {})[index] = kept
    for name, found in images.items():
        thumbs = [dd.first_screen(found[i]) for i in sorted(found)]
        per_draft[name] = [dd.image_similarity(a, b) for i, a in enumerate(thumbs) for b in thumbs[i + 1 :]]
    values = [value for scores in per_draft.values() for value in scores]
    return {
        "perDraft": per_draft,
        "mean": round(statistics.mean(values), 4) if values else None,
        "max": max(values) if values else None,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--engine", default="fake", help="drafting engine (default: fake)")
    parser.add_argument("--runs", type=int, default=5, help="drafts of the same brief (default: 5)")
    parser.add_argument("--screenshots", action="store_true", help="build each direction and compare first screens")
    asyncio.run(main(parser.parse_args()))
