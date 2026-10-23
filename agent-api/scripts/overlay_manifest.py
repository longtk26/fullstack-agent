"""Regenerates templates/fastapi_overlay/overlay.json after a deliberate template.lock bump.

    python -m scripts.overlay_manifest <template checkout>

Every overlay file that replaces a template file records the template file's sha256, so a template change is
detected (TEMPLATE_DRIFT) instead of silently overwritten.
"""

import hashlib
import json
import sys
from pathlib import Path

OVERLAY = Path(__file__).resolve().parent.parent / "templates" / "fastapi_overlay"
REMOVE = [
    "src/modules/users",
    "src/modules/shared/domain/entities/user_entity.py",
    "src/modules/shared/infrastructure/models/user_model.py",
    "alembic/versions/9a87df8ba9ec_create_user_table.py",
]
VERSION = "1"


def main(template: Path) -> None:
    lock = dict(
        line.split("=", 1) for line in (OVERLAY.parent / "template.lock").read_text().splitlines() if "=" in line
    )
    replace, add = {}, []
    for path in sorted((OVERLAY / "files").rglob("*")):
        relative = path.relative_to(OVERLAY / "files").as_posix()
        if not path.is_file() or "_cache/" in relative or "__pycache__" in relative:
            continue
        original = template / relative
        if original.is_file():
            replace[relative] = hashlib.sha256(original.read_bytes()).hexdigest()
        else:
            add.append(relative)
    for relative in REMOVE:
        if not (template / relative).exists():
            raise SystemExit(f"remove target missing from template: {relative}")
    manifest = {"version": VERSION, "templateCommit": lock["commit"], "replace": replace, "add": add, "remove": REMOVE}
    (OVERLAY / "overlay.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"{len(replace)} replaced, {len(add)} added, {len(REMOVE)} removed")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
