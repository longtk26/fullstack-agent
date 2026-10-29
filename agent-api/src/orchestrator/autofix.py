"""Mechanical fixes before validation (Story 17.5), so the repair loop (an engine call) starts only for what a tool
cannot fix.

    1 owned files  generator-owned files the engine changed or removed go back to their scaffold version
    2 autofix      backend: ruff check --fix + ruff format; frontend: eslint --fix (on the files the engine may edit)

Both run at the start of the validate node and are committed as `node:autofix attempt:<n>` when they change
anything. Added files under owned paths are left alone: the conventions check reports them, as before.
"""

import hashlib
import json
import shlex
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from src.sandbox import ISandbox

from . import tracing
from .checks.frontend_conventions import SKIP_DIRS as FRONTEND_SKIP_DIRS
from .context import JobContext
from .validation import SKIP_DIRS as BACKEND_SKIP_DIRS
from .workspace import JobWorkspace, WorkspaceManager

Repo = Literal["project", "frontend"]
OWNED_INFO = ".bga/owned.json"
SCAFFOLD_COMMIT = {"project": "^node:scaffold$", "frontend": "^node:scaffold_frontend "}
SOURCES = {"project": (".py",), "frontend": (".ts", ".tsx", ".js", ".jsx", ".mjs")}
SKIP = {"project": BACKEND_SKIP_DIRS, "frontend": FRONTEND_SKIP_DIRS}
# The frontend engine writes under src/ only; next-env.d.ts, public/mockServiceWorker.js etc. belong to their tools.
ROOTS = {"project": None, "frontend": "src"}


@dataclass
class AutofixResult:
    restored: list[str] = field(default_factory=list)
    fixed: list[str] = field(default_factory=list)
    duration_ms: int = 0

    @property
    def changed(self) -> bool:
        return bool(self.restored or self.fixed)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _owned(project: Path) -> dict[str, str]:
    path = project / OWNED_INFO
    return json.loads(path.read_text()) if path.is_file() else {}


def restore_owned(workspaces: WorkspaceManager, workspace: JobWorkspace, repo: Repo) -> list[str]:
    """Owned files that differ from their recorded hash, put back from the scaffold commit. A file is restored only
    when the commit holds exactly the recorded version; anything else stays for the conventions check."""
    project = workspace.repo(repo)
    recorded = _owned(project)
    changed = [
        relative
        for relative, digest in recorded.items()
        if not (project / relative).is_file() or _sha256((project / relative).read_bytes()) != digest
    ]
    if not changed:
        return []
    sha = workspaces.node_commit(workspace, SCAFFOLD_COMMIT[repo], repo=repo)
    if sha is None:
        return []
    restorable = []
    for relative in sorted(changed):
        content = workspaces.file_at(workspace, sha, relative, repo=repo)
        if content is not None and _sha256(content) == recorded[relative]:
            restorable.append(relative)
    workspaces.checkout_paths(workspace, sha, restorable, repo=repo)
    return restorable


def fixable_files(project: Path, repo: Repo) -> list[str]:
    """Source files the engine may edit: the lane's extensions, outside tool/output folders and owned files."""
    owned = set(_owned(project))
    files = []
    for path in sorted(project.rglob("*")):
        relative = path.relative_to(project)
        if (
            path.suffix in SOURCES[repo]
            and (ROOTS[repo] is None or relative.parts[0] == ROOTS[repo])
            and path.is_file()
            and not SKIP[repo] & set(relative.parts[:-1])
            and relative.as_posix() not in owned
        ):
            files.append(relative.as_posix())
    return files


def _command(repo: Repo, files: list[str]) -> str:
    quoted = " ".join(shlex.quote(name) for name in files)
    if repo == "project":
        # Safe fixes only; unfixable findings (and syntax errors) stay for the lint check and the repair loop.
        return f"ruff check --fix --exit-zero -q {quoted} ; ruff format -q {quoted} ; true"
    return f"pnpm exec eslint --fix --no-warn-ignored {quoted} >/dev/null 2>&1 ; true"


async def _prepare_frontend(sandbox: ISandbox) -> bool:
    """eslint needs node_modules: the shared one (17.5) or an offline install. False when neither works (new
    packages): autofix is skipped and the install check reports the problem."""
    if await sandbox.shared_dependencies():
        return True
    return (await sandbox.exec("pnpm install --frozen-lockfile --offline", timeout_s=600)).ok


async def autofix(
    workspaces: WorkspaceManager, workspace: JobWorkspace, repo: Repo, sandbox: ISandbox | None
) -> AutofixResult:
    """Restores owned files, then runs the lane's fixer in the sandbox. Without a sandbox only owned files are
    restored (nothing runs generated tooling outside it)."""
    started = time.monotonic()
    with tracing.span("autofix", "chain", inputs={"repo": repo}) as span:
        result = AutofixResult(restored=restore_owned(workspaces, workspace, repo))
        project = workspace.repo(repo)
        files = fixable_files(project, repo)
        if sandbox is not None and files and (repo == "project" or await _prepare_frontend(sandbox)):
            before = {name: _sha256((project / name).read_bytes()) for name in files}
            await sandbox.exec(_command(repo, files), timeout_s=300)
            result.fixed = [
                name
                for name, digest in before.items()
                if not (project / name).is_file() or _sha256((project / name).read_bytes()) != digest
            ]
        result.duration_ms = int((time.monotonic() - started) * 1000)
        span.end(outputs={"restored": result.restored, "fixed": result.fixed, "durationMs": result.duration_ms})
    return result


async def autofix_before_validation(ctx: JobContext, repo: Repo, attempt: int, step: str) -> dict[str, int]:
    """The validate nodes' first step: fix, commit as `node:autofix`, announce `validation.autofix`."""
    sandbox = await (ctx.sandbox() if repo == "project" else ctx.frontend_sandbox())
    result = await autofix(ctx.workspaces, ctx.workspace, repo, sandbox)
    if not result.changed:
        return {}
    async with ctx._commit_lock:
        ctx.workspaces.commit(ctx.workspace, f"node:autofix attempt:{attempt}", repo=repo)
    await ctx.emit(
        "validation.autofix",
        step=step,
        fixed=result.fixed,
        restored=result.restored,
        durationMs=result.duration_ms,
        attempt=attempt,
    )
    return {"autofixed": len(result.fixed), "restoredOwned": len(result.restored)}
