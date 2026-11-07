"""The draft answer envelope (Story 18.10), shared by every draft engine that answers in one JSON object.

{"files": {"frontend-spec.json": {...}},                     # written whole (objects dumped as JSON)
 "patches": {"backend-spec.json": [{"op": "replace", ...}]},  # RFC 6902, applied to the file already there
 "message": "what was done"}
"""

import json
from pathlib import Path
from typing import Any

from src.libs.jsonpatch import PatchError, apply_patch

from .workspace import ensure_inside


def apply_envelope(workdir: Path, envelope: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Writes the envelope's files and applies its patches; returns (changed files, problems)."""
    changed: list[str] = []
    problems: list[str] = []
    files = envelope.get("files") or {}
    if not isinstance(files, dict):
        problems.append("'files' is not an object")
        files = {}
    for relative, content in files.items():
        try:
            target = ensure_inside(workdir / str(relative), workdir)
        except Exception as exc:  # outside the workdir, or an odd name
            problems.append(f"{relative}: {exc}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        text = content if isinstance(content, str) else json.dumps(content, indent=2, ensure_ascii=False) + "\n"
        target.write_text(text)
        changed.append(str(relative))
    patches = envelope.get("patches") or {}
    if not isinstance(patches, dict):
        problems.append("'patches' is not an object")
        patches = {}
    for relative, patch in patches.items():
        try:
            target = ensure_inside(workdir / str(relative), workdir)
            document = json.loads(target.read_text())
        except Exception as exc:
            problems.append(f"{relative}: cannot patch ({exc})")
            continue
        if not isinstance(patch, list):
            problems.append(f"{relative}: 'patches' entry is not a list")
            continue
        try:
            patched = apply_patch(document, patch)
        except PatchError as exc:
            # Apply the operations before the failing one, so one bad pointer does not undo the round.
            problems.append(f"{relative}: {exc}")
            if exc.index == 0:
                continue
            patched = apply_patch(document, patch[: exc.index])
        target.write_text(json.dumps(patched, indent=2, ensure_ascii=False) + "\n")
        if str(relative) not in changed:
            changed.append(str(relative))
    return changed, problems
