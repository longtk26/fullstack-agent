import shutil

import pytest

from src.orchestrator.scaffold import (
    OWNED_INFO,
    TemplateDrift,
    changed_owned,
    check_template,
    record_owned,
    scaffold_project,
)
from tests.generation_helpers import TEMPLATE


def test_scaffold_applies_overlay_and_removes_the_sample_module(tmp_path):
    info = scaffold_project(TEMPLATE, tmp_path, "Acme Store")

    assert info["templateRef"] and info["overlayVersion"]
    assert not (tmp_path / "src/modules/users").exists()
    assert not list((tmp_path / "alembic/versions").glob("*.py"))
    assert "ConflictException" in (tmp_path / "src/libs/exceptions/base_exception.py").read_text()
    assert 'app_name: str = "Acme Store"' in (tmp_path / "src/configs/config.py").read_text()
    assert (tmp_path / "docker-entrypoint.sh").stat().st_mode & 0o111
    assert (tmp_path / "tests/conftest.py").exists()


def test_without_dockerfile_the_docker_files_are_removed(tmp_path):
    scaffold_project(TEMPLATE, tmp_path, "X", generate_dockerfile=False)

    assert not (tmp_path / "Dockerfile").exists() and not (tmp_path / "docker-entrypoint.sh").exists()


def test_template_drift_is_detected_before_writing(tmp_path):
    template = tmp_path / "template"
    shutil.copytree(TEMPLATE, template, ignore=shutil.ignore_patterns(".git"))
    (template / "src/main.py").write_text("# changed upstream\n")
    project = tmp_path / "project"
    project.mkdir()

    with pytest.raises(TemplateDrift) as raised:
        scaffold_project(template, project, "X")

    assert "src/main.py: changed" in raised.value.problems
    assert list(project.iterdir()) == []
    assert check_template(TEMPLATE) == []


def test_owned_file_changes_are_detected(tmp_path):
    scaffold_project(TEMPLATE, tmp_path, "X")
    record_owned(tmp_path)
    assert (tmp_path / OWNED_INFO).exists() and changed_owned(tmp_path) == []

    (tmp_path / "src/main.py").write_text("app = None\n")
    (tmp_path / "src/libs/extra.py").write_text("x = 1\n")

    assert changed_owned(tmp_path) == ["src/libs/extra.py", "src/main.py"]
