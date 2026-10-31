"""Base project = pinned fastapi-skills template + our overlay (Story 5.2).

The overlay manifest records the sha256 of every template file it replaces; if the template ever differs, the
job fails with TEMPLATE_DRIFT before anything is written (never a half-patched project).
"""

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

OVERLAY_DIR = Path(__file__).resolve().parents[2] / "templates" / "fastapi_overlay"
PLACEHOLDER = "{{PROJECT_NAME}}"
DOCKER_FILES = ("Dockerfile", "docker-entrypoint.sh", "docker-compose.yml", ".dockerignore")
# Generator-owned: the engine must not change them (checked by the conventions check).
OWNED = (
    "src/main.py",
    "src/libs",
    "src/configs",
    "alembic/env.py",
    "alembic.ini",
    "tests/conftest.py",
    "scripts/seed.py",
    "docker-entrypoint.sh",
    "pyproject.toml",
    "requirements-dev.txt",
    "Makefile",
)
SCAFFOLD_INFO = ".bga/scaffold.json"
CACHE_DIRS = {".git", "__pycache__", ".ruff_cache", ".pytest_cache", ".venv"}
OWNED_INFO = ".bga/owned.json"


class TemplateDrift(Exception):
    def __init__(self, problems: list[str]):
        super().__init__("Template does not match the overlay manifest: " + "; ".join(problems[:10]))
        self.problems = problems


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest(overlay: Path = OVERLAY_DIR) -> dict[str, Any]:
    return json.loads((overlay / "overlay.json").read_text())


def check_template(template: Path, overlay: Path = OVERLAY_DIR) -> list[str]:
    manifest = load_manifest(overlay)
    problems = []
    if not template.is_dir():
        return [f"template directory missing: {template}"]
    for relative, expected in manifest["replace"].items():
        path = template / relative
        if not path.is_file():
            problems.append(f"{relative}: missing")
        elif _sha256(path) != expected:
            problems.append(f"{relative}: changed")
    for relative in manifest["remove"]:
        if not (template / relative).exists():
            problems.append(f"{relative}: expected to remove, not found")
    for relative in manifest["add"]:
        if (template / relative).exists():
            problems.append(f"{relative}: template now ships this file")
    return problems


def scaffold_project(
    template: Path,
    project: Path,
    project_name: str,
    generate_dockerfile: bool = True,
    overlay: Path = OVERLAY_DIR,
    seed_assets_note: str = "",
) -> dict[str, Any]:
    problems = check_template(template, overlay)
    if problems:
        raise TemplateDrift(problems)
    manifest = load_manifest(overlay)

    for source in template.rglob("*"):
        relative = source.relative_to(template)
        if CACHE_DIRS & set(relative.parts):
            continue
        target = project / relative
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    for relative in manifest["remove"]:
        target = project / relative
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink(missing_ok=True)
    files = overlay / "files"
    for source in sorted(files.rglob("*")):
        relative = source.relative_to(files)
        if not source.is_file() or CACHE_DIRS & set(relative.parts):
            continue
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        content = source.read_bytes()
        if PLACEHOLDER.encode() in content:
            content = content.replace(PLACEHOLDER.encode(), project_name.encode())
        if b"{{SEED_ASSETS_NOTE}}" in content:
            replacement = f"\n\n{seed_assets_note}\n" if seed_assets_note else ""
            content = content.replace(b"\n{{SEED_ASSETS_NOTE}}", replacement.encode())
            content = content.replace(b"{{SEED_ASSETS_NOTE}}", replacement.encode())
        target.write_bytes(content)
        target.chmod(source.stat().st_mode & 0o777)
    if not generate_dockerfile:
        for relative in DOCKER_FILES:
            (project / relative).unlink(missing_ok=True)

    info = {
        "templateRef": manifest["templateCommit"],
        "overlayVersion": manifest["version"],
        "generateDockerfile": generate_dockerfile,
    }
    info_path = project / SCAFFOLD_INFO
    info_path.parent.mkdir(parents=True, exist_ok=True)
    info_path.write_text(json.dumps(info, indent=2) + "\n")
    return info


def owned_files(project: Path) -> list[Path]:
    paths: list[Path] = []
    for relative in OWNED:
        path = project / relative
        if path.is_dir():
            paths.extend(p for p in sorted(path.rglob("*.py")) if "__pycache__" not in p.parts)
        elif path.is_file():
            paths.append(path)
    return paths


def record_owned(project: Path) -> dict[str, str]:
    hashes = {p.relative_to(project).as_posix(): _sha256(p) for p in owned_files(project)}
    (project / OWNED_INFO).write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n")
    return hashes


def add_owned(project: Path, files: list[str]) -> None:
    """Records files the generator wrote after the scaffold (Story 17.6: CRUD code from templates) as owned."""
    path = project / OWNED_INFO
    hashes = json.loads(path.read_text()) if path.exists() else {}
    hashes |= {relative: _sha256(project / relative) for relative in files if (project / relative).is_file()}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n")


def changed_owned(project: Path) -> list[str]:
    """Owned files the engine changed, added or removed since the scaffold (or since they were generated)."""
    recorded_path = project / OWNED_INFO
    if not recorded_path.exists():
        return []
    recorded: dict[str, str] = json.loads(recorded_path.read_text())
    current = {p.relative_to(project).as_posix(): _sha256(p) for p in owned_files(project)}
    current |= {path: _sha256(project / path) for path in recorded if (project / path).is_file()}
    return sorted(path for path in recorded.keys() | current.keys() if recorded.get(path) != current.get(path))
