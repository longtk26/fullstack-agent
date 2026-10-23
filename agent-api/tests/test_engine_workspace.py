import pytest

from src.engines.workspace import (
    WorkspaceViolation,
    changed_files,
    ensure_inside,
    install_skills,
    snapshot,
    write_managed_section,
)


def test_ensure_inside_rejects_escapes(tmp_path):
    root = tmp_path / "root"
    (root / "job").mkdir(parents=True)
    (root / "link").symlink_to(tmp_path)

    assert ensure_inside(root / "job", root) == (root / "job").resolve()
    with pytest.raises(WorkspaceViolation):
        ensure_inside(root / ".." / "elsewhere", root)
    with pytest.raises(WorkspaceViolation):
        ensure_inside(root / "link", root)


def test_snapshot_diff_reports_added_modified_deleted_and_ignores_git(tmp_path):
    (tmp_path / "keep.py").write_text("a")
    (tmp_path / "edit.py").write_text("a")
    (tmp_path / "gone.py").write_text("a")
    before = snapshot(tmp_path)

    (tmp_path / "edit.py").write_text("changed")
    (tmp_path / "gone.py").unlink()
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "new.py").write_text("n")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "index").write_text("x")

    assert changed_files(before, snapshot(tmp_path)) == ["edit.py", "gone.py", "pkg/new.py"]


def test_managed_section_is_appended_once_and_replaced_in_place(tmp_path):
    target = tmp_path / "CLAUDE.md"
    target.write_text("# Template guide\n")

    write_managed_section(target, "rule v1")
    write_managed_section(target, "rule v2")

    text = target.read_text()
    assert text.startswith("# Template guide")
    assert text.count("BEGIN bga-conventions") == 1
    assert "rule v2" in text and "rule v1" not in text


def test_install_skills_replaces_stale_copies(tmp_path):
    skill = tmp_path / "src" / "fastapi-skills"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("v2")
    target = tmp_path / "ws" / ".claude" / "skills"
    (target / "fastapi-skills").mkdir(parents=True)
    (target / "fastapi-skills" / "old.md").write_text("stale")

    install_skills([skill], target)

    assert (target / "fastapi-skills" / "SKILL.md").read_text() == "v2"
    assert not (target / "fastapi-skills" / "old.md").exists()
