import hashlib
import re
import shutil
from pathlib import Path

SNAPSHOT_EXCLUDES = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache"}
_SECTION = "bga-conventions"


class WorkspaceViolation(ValueError):
    pass


def ensure_inside(path: Path, root: Path) -> Path:
    """Resolves symlinks before comparing, so a link pointing out of the root is rejected."""
    resolved, resolved_root = path.resolve(), root.resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise WorkspaceViolation(f"{path} is outside the allowed root {root}")
    return resolved


def snapshot(root: Path, extra_excludes: set[str] = frozenset()) -> dict[str, tuple[int, int]]:
    excludes = SNAPSHOT_EXCLUDES | set(extra_excludes)
    state: dict[str, tuple[int, int]] = {}
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if any(part in excludes for part in rel.parts) or not path.is_file():
            continue
        stat = path.stat()
        state[rel.as_posix()] = (stat.st_size, stat.st_mtime_ns)
    return state


def changed_files(before: dict[str, tuple[int, int]], after: dict[str, tuple[int, int]]) -> list[str]:
    return sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))


def install_skills(skill_dirs: list[Path], target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for skill in skill_dirs:
        destination = target / skill.name
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(skill, destination)


def directory_sha256(directory: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in directory.rglob("*") if p.is_file()):
        digest.update(path.relative_to(directory).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def write_managed_section(path: Path, body: str) -> None:
    """Adds or replaces our section in a context file, leaving the rest (e.g. the template's CLAUDE.md) intact."""
    begin, end = f"<!-- BEGIN {_SECTION} -->", f"<!-- END {_SECTION} -->"
    block = f"{begin}\n{body.strip()}\n{end}\n"
    existing = path.read_text() if path.exists() else ""
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end) + r"\n?", re.DOTALL)
    if pattern.search(existing):
        updated = pattern.sub(lambda _: block, existing)
    else:
        updated = f"{existing.rstrip()}\n\n{block}" if existing.strip() else block
    path.write_text(updated)


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
