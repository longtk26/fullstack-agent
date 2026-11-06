"""Designing a drafted site's pages as element trees (Epic 21, Story 21.6). No LLM here: this module prepares one
`draft_tree` request per page (and one for the chrome), reads what the engine wrote, lets the tree rules repair it,
for a static site. A page whose tree still breaks the rules keeps its sections.
"""

import copy
import json
from pathlib import Path
from typing import Any

from src.modules.shared.domain.frontend_spec import validate_frontend_spec_data
from src.modules.shared.domain.frontend_spec.normalizer import page_id
from src.modules.shared.domain.frontend_spec.trees import (
    MAX_DEPTH,
    MAX_NODES,
    allowed_types_markdown,
    check_tree,
    fix_trees,
    tree_collections,
)

TREES_DIR = "trees"
CHROME = "chrome"
SAMPLE_RECORDS = 2


def _note(path: str, message: str) -> dict[str, Any]:
    return {"spec": "frontend", "path": path, "message": message, "suggestion": None}


def tree_requests(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """One request per page (its content outline is its sections) plus the chrome."""
    requests = []
    for page in spec.get("pages") or []:
        pid = page.get("id") or page_id(page["route"])
        requests.append(
            {
                "id": pid,
                "route": page["route"],
                "title": page["title"],
                "purpose": page.get("purpose"),
                "sections": _outline(page.get("sections") or []),
                "output_path": f"{TREES_DIR}/{pid}.json",
            }
        )
    requests.append(
        {
            "id": CHROME,
            "route": "/",
            "title": "Site chrome",
            "purpose": None,
            "sections": [],
            "output_path": f"{TREES_DIR}/{CHROME}.json",
        }
    )
    return requests


def _outline(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sections as a content outline: component, content, data binding, nested children; no renderer details."""
    out = []
    for section in sections:
        item = {k: v for k, v in section.items() if k in ("id", "component", "content", "data", "form")}
        if section.get("children"):
            item["children"] = _outline(section["children"])
        out.append(item)
    return out


def direction_brief(spec: dict[str, Any]) -> dict[str, Any]:
    theme = spec.get("theme") or {}
    direction = theme.get("direction") or {}
    return {
        "name": direction.get("name") or theme.get("style"),
        "concept": direction.get("concept"),
        "tone": direction.get("tone"),
        "keyVisual": direction.get("keyVisual"),
        "fonts": {
            "heading": (theme.get("typography") or {}).get("headingFont"),
            "body": (theme.get("typography") or {}).get("bodyFont"),
        },
        "colors": theme.get("colors"),
        "colorArea": theme.get("colorArea"),
        "surface": theme.get("surface"),
        "radius": theme.get("radius"),
        "density": theme.get("density"),
        "icons": theme.get("icons"),
        "motion": theme.get("motion"),
    }


def collections_brief(spec: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for item in spec.get("content") or []:
        records = [r for r in item.get("records") or [] if isinstance(r, dict)]
        fields = sorted({key for record in records for key in record})
        out.append({"key": item["collection"], "fields": fields, "sample": records[0] if records else {}})
    return out


def prompt_context(spec: dict[str, Any], request: dict[str, Any], inline: bool) -> dict[str, Any]:
    pages = [
        {"id": p.get("id") or page_id(p["route"]), "title": p["title"], "route": p["route"]}
        for p in spec.get("pages") or []
    ]
    assets = [
        {"id": a["id"], "alt": a.get("alt") or "", "kind": a.get("kind", "image")} for a in spec.get("assets") or []
    ]
    return {
        "page": request,
        "direction": direction_brief(spec),
        "pages": pages,
        "collections": collections_brief(spec),
        "assets": assets,
        "allowed_types": allowed_types_markdown(),
        "mode": spec["project"]["mode"],
        "inline": inline,
        "output_path": request["output_path"],
        "max_nodes": MAX_NODES,
        "max_depth": MAX_DEPTH,
    }


def apply_tree_files(work: Path, spec_file: Path) -> list[dict[str, Any]]:
    """Reads `trees/<page>.json` into the spec's pages (and `trees/chrome.json` into the layout), repairs them with
    the tree rules, and keeps the sections for any page whose tree still has errors. Writes the spec back."""
    spec = json.loads(spec_file.read_text())
    notes: list[dict[str, Any]] = []
    before = copy.deepcopy(spec)
    pages = {page.get("id") or page_id(page["route"]): page for page in spec.get("pages") or []}
    applied = 0
    for pid, page in pages.items():
        path = work / TREES_DIR / f"{pid}.json"
        if not path.is_file():
            notes.append(
                _note(f"/pages/{list(pages).index(pid)}", f"Page '{pid}': no designed tree; its sections render")
            )
            continue
        try:
            data = json.loads(path.read_text())
        except ValueError as exc:
            notes.append(
                _note(
                    f"/pages/{list(pages).index(pid)}/tree",
                    f"Page '{pid}': tree is not JSON ({exc}); its sections render",
                )
            )
            continue
        tree = data.get("tree") if isinstance(data, dict) else None
        if not isinstance(tree, dict):
            notes.append(
                _note(
                    f"/pages/{list(pages).index(pid)}/tree", f"Page '{pid}': no tree in the answer; its sections render"
                )
            )
            continue
        page["tree"] = tree
        if isinstance(data.get("css"), str) and data["css"].strip():
            page["css"] = data["css"][:20_000]
        applied += 1
    chrome_file = work / TREES_DIR / f"{CHROME}.json"
    if chrome_file.is_file():
        try:
            data = json.loads(chrome_file.read_text())
            header, footer = data.get("tree"), data.get("footer")
            if isinstance(header, dict):
                spec.setdefault("layout", {})["chrome"] = header
            if isinstance(footer, dict):
                spec.setdefault("layout", {})["footerTree"] = footer
        except ValueError:
            notes.append(_note("/layout/chrome", "The chrome answer is not JSON; the shell's own header renders"))
    if not applied and "chrome" not in (spec.get("layout") or {}):
        return notes
    spec, fix_notes = fix_trees(spec)
    notes.extend(fix_notes)
    # A tree that still breaks a rule (an unknown asset, too deep) costs the page its design, not the draft.
    collections = tree_collections(spec)
    page_ids = set(pages)
    asset_ids = {a.get("id") for a in spec.get("assets") or [] if isinstance(a, dict)}
    for index, page in enumerate(spec.get("pages") or []):
        if not page.get("tree"):
            continue
        issues = check_tree(page["tree"], f"/pages/{index}/tree", page_ids, asset_ids, collections)
        errors = [i for i in issues if not i["warning"]]
        if errors:
            notes.append(
                _note(f"/pages/{index}/tree", f"Designed page dropped ({errors[0]['message']}); its sections render")
            )
            page.pop("tree", None)
            page.pop("css", None)
            if not page.get("sections"):
                page["sections"] = before["pages"][index].get("sections") or []
    layout = spec.get("layout") or {}
    for key in ("chrome", "footerTree"):
        if isinstance(layout.get(key), dict):
            errors = [
                i
                for i in check_tree(layout[key], f"/layout/{key}", page_ids, asset_ids, collections)
                if not i["warning"]
            ]
            if errors:
                notes.append(_note(f"/layout/{key}", f"Designed {key} dropped ({errors[0]['message']})"))
                layout.pop(key)
    result = validate_frontend_spec_data(spec)
    if not result.report.valid:
        notes.append(_note("/pages", f"Designed pages dropped: {result.report.errors[0].message}; the sections render"))
        spec = before
    spec_file.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n")
    return notes
