import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from src.engines.workspace import ensure_inside

# safe.directory: sandbox containers (another uid) also write into the project.
_GIT = [
    "git",
    "-c",
    "user.name=bga",
    "-c",
    "user.email=bga@localhost",
    "-c",
    "commit.gpgsign=false",
    "-c",
    "safe.directory=*",
]


class DiskLimitExceeded(RuntimeError):
    pass


@dataclass(frozen=True)
class JobWorkspace:
    root: Path

    @property
    def project(self) -> Path:
        return self.root / "project"

    @property
    def spec_dir(self) -> Path:
        return self.root / "spec"

    @property
    def reports(self) -> Path:
        return self.root / "reports"

    @property
    def state(self) -> Path:
        """Engine homes and logs: outside the project so they never end up in the generated code."""
        return self.root / "state"


class WorkspaceManager:
    def __init__(self, root: Path, max_mb: int):
        self.root = root
        self.max_mb = max_mb

    def path_for(self, generation_id: str) -> JobWorkspace:
        return JobWorkspace(ensure_inside(self.root / generation_id, self.root))

    def create(self, generation_id: str) -> JobWorkspace:
        workspace = self.path_for(generation_id)
        for directory in (workspace.project, workspace.spec_dir, workspace.reports, workspace.state):
            directory.mkdir(parents=True, exist_ok=True)
        workspace.root.chmod(0o700)
        if not (workspace.project / ".git").exists():
            self._git(workspace, "init", "-q", "-b", "main")
            self._git(workspace, "commit", "-q", "--allow-empty", "-m", "workspace created")
        return workspace

    def commit(self, workspace: JobWorkspace, message: str) -> str:
        self._git(workspace, "add", "-A")
        self._git(workspace, "commit", "-q", "--allow-empty", "-m", message)
        return self._git(workspace, "rev-parse", "HEAD").strip()

    def reset_to(self, workspace: JobWorkspace, sha: str) -> None:
        """Drops anything a crashed node half-wrote, back to the last node that completed."""
        self._git(workspace, "reset", "-q", "--hard", sha)
        self._git(workspace, "clean", "-q", "-fdx")

    def repair_patches(self, workspace: JobWorkspace) -> list[tuple[str, str]]:
        """(name, diff) per `node:repair_code` commit, oldest first: what each repair attempt changed."""
        log = self._git(workspace, "log", "--reverse", "--format=%H %s", "--grep=^node:repair_code ")
        patches = []
        for line in log.splitlines():
            sha, _, subject = line.partition(" ")
            attempt = subject.rsplit("attempt:", 1)[-1]
            patches.append((f"repair-{attempt}.patch", self._git(workspace, "show", "--format=", "--binary", sha)))
        return patches

    def head_stats(self, workspace: JobWorkspace) -> dict[str, int]:
        """Files, insertions and deletions of the last commit (a repair attempt's diff stats, Story 8.2)."""
        stats = {"files": 0, "insertions": 0, "deletions": 0}
        for line in self._git(workspace, "show", "--numstat", "--format=", "HEAD").splitlines():
            added, deleted, _ = (line.split("\t", 2) + ["", ""])[:3]
            stats["files"] += 1
            stats["insertions"] += int(added) if added.isdigit() else 0
            stats["deletions"] += int(deleted) if deleted.isdigit() else 0
        return stats

    def check_size(self, workspace: JobWorkspace) -> int:
        size = sum(
            path.stat().st_size
            for path in workspace.root.rglob("*")
            if path.is_file() and not path.is_symlink() and ".venv" not in path.parts
        )
        megabytes = size // (1024 * 1024)
        if megabytes > self.max_mb:
            raise DiskLimitExceeded(f"Workspace uses {megabytes} MB (limit {self.max_mb} MB)")
        return megabytes

    def delete(self, generation_id: str) -> None:
        shutil.rmtree(self.path_for(generation_id).root, ignore_errors=True)

    def existing_ids(self) -> list[str]:
        return [path.name for path in self.root.iterdir() if path.is_dir()] if self.root.exists() else []

    @staticmethod
    def _git(workspace: JobWorkspace, *args: str) -> str:
        completed = subprocess.run(
            [*_GIT, *args], cwd=workspace.project, capture_output=True, text=True, check=False, timeout=120
        )
        if completed.returncode != 0:
            raise RuntimeError(f"git {args[0]} failed: {completed.stderr.strip()[:500]}")
        return completed.stdout
