import pytest

from src.engines.workspace import WorkspaceViolation
from src.orchestrator.workspace import DiskLimitExceeded, WorkspaceManager


def test_commit_and_reset_discard_partial_writes(tmp_path):
    manager = WorkspaceManager(tmp_path, max_mb=10)
    workspace = manager.create("gen_1")
    (workspace.project / "kept.py").write_text("x = 1\n")
    sha = manager.commit(workspace, "node:a")

    (workspace.project / "kept.py").write_text("x = 'half written'\n")
    (workspace.project / "stray.py").write_text("partial\n")
    manager.reset_to(workspace, sha)

    assert (workspace.project / "kept.py").read_text() == "x = 1\n"
    assert not (workspace.project / "stray.py").exists()


def test_layout_and_permissions(tmp_path):
    workspace = WorkspaceManager(tmp_path, max_mb=10).create("gen_2")

    assert {p.name for p in workspace.root.iterdir()} == {"project", "spec", "reports", "state"}
    assert oct(workspace.root.stat().st_mode & 0o777) == "0o700"


def test_disk_limit(tmp_path):
    manager = WorkspaceManager(tmp_path, max_mb=1)
    workspace = manager.create("gen_3")
    (workspace.reports / "big.bin").write_bytes(b"x" * (3 * 1024 * 1024))

    with pytest.raises(DiskLimitExceeded):
        manager.check_size(workspace)


def test_generation_ids_cannot_escape_the_root(tmp_path):
    with pytest.raises(WorkspaceViolation):
        WorkspaceManager(tmp_path, max_mb=1).path_for("../elsewhere")
