"""Writes schemas/backend-spec-<version>.json for every supported version (`make schema`)."""

import json
from pathlib import Path

from src.modules.shared.domain.backend_spec import spec_json_schema, supported_versions

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"


def render(version: str) -> str:
    return json.dumps(spec_json_schema(version), indent=2, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    for version in supported_versions():
        target = SCHEMA_DIR / f"backend-spec-{version}.json"
        target.write_text(render(version))
        print(f"wrote {target}")
