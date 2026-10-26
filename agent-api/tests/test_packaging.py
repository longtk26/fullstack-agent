import io
import json
import zipfile
from pathlib import Path

from src.engines.workspace import write_managed_section
from src.orchestrator.packaging import (
    build_seed,
    build_source_zip,
    env_variables,
    operations_from_openapi,
    operations_from_plan,
)

PLANS = Path(__file__).parent / "fixtures" / "plans"
OVERLAY = Path(__file__).parents[1] / "templates" / "fastapi_overlay" / "files"


def _project(root: Path) -> Path:
    project = root / "project"
    files = {
        "src/main.py": "app = None\n",
        "src/modules/tasks/__pycache__/x.cpython-312.pyc": "",
        ".venv/bin/python": "",
        ".git/HEAD": "ref: refs/heads/main\n",
        ".bga/plan.json": "{}",
        ".claude/skills/fastapi-skills/SKILL.md": "skill",
        ".agents/skills/fastapi-skills/SKILL.md": "skill",
        ".env": "DB_URL=postgresql://app:secret@db/app\n",
        ".env.ex": "DB_URL=postgresql://app:app@localhost:5432/app\n",
        "CLAUDE.md": "# Template guide\n",
        "docker-entrypoint.sh": "#!/bin/sh\n",
    }
    for relative, content in files.items():
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    (project / "docker-entrypoint.sh").chmod(0o755)
    write_managed_section(project / "CLAUDE.md", "generator rules")
    write_managed_section(project / "AGENTS.md", "generator rules")
    return project


def test_source_zip_ships_only_the_project(tmp_path):
    project = _project(tmp_path)

    archive = zipfile.ZipFile(io.BytesIO(build_source_zip(project)))

    assert archive.namelist() == [".env.ex", "CLAUDE.md", "docker-entrypoint.sh", "src/main.py"]
    assert archive.read("CLAUDE.md").decode() == "# Template guide\n", "our context section is stripped"
    assert archive.getinfo("docker-entrypoint.sh").external_attr >> 16 == 0o100755
    assert archive.getinfo("src/main.py").date_time == (1980, 1, 1, 0, 0, 0)


def test_source_zip_is_byte_for_byte_reproducible(tmp_path):
    project = _project(tmp_path)
    first = build_source_zip(project)
    (project / "src" / "main.py").touch()  # a newer mtime must not change the archive

    assert build_source_zip(project) == first


def test_manifest_operations_come_from_the_exported_openapi():
    plan = json.loads((PLANS / "two-entity.plan.json").read_text())
    document = {
        "paths": {
            "/health": {"get": {"operationId": "health_check", "responses": {"200": {}}}},
            "/tasks": {
                "post": {
                    "operationId": "task.create",
                    "requestBody": {
                        "content": {"application/json": {"schema": {"$ref": "#/c/s/CreateTaskRequestDto"}}}
                    },
                    "responses": {
                        "201": {"content": {"application/json": {"schema": {"$ref": "#/c/s/TaskResponseDto"}}}},
                        "422": {},
                    },
                },
            },
        }
    }

    operations = operations_from_openapi(document, plan)

    assert operations == [
        {
            "operationId": "task.create",
            "method": "POST",
            "path": "/tasks",
            "auth": "none",
            "requestSchema": "CreateTaskRequestDto",
            "responseSchema": "TaskResponseDto",
            "statusCodes": [201, 422],
        }
    ]


def test_plan_fallback_lists_every_planned_operation():
    plan = json.loads((PLANS / "two-entity.plan.json").read_text())

    operations = operations_from_plan(plan)

    assert len(operations) == sum(len(m["operations"]) for m in plan["modules"])
    create = next(op for op in operations if op["operationId"] == "task.create")
    assert create["statusCodes"][0] == 201 and create["responseSchema"] == "TaskResponseDto"


def test_env_variables_from_the_overlay():
    variables = {v["name"]: v for v in env_variables(OVERLAY)}

    assert variables["DB_URL"]["required"] and variables["DB_URL"]["secret"]
    assert not variables["PORT"]["required"] and not variables["PORT"]["secret"]
    assert "pytest" in variables["TEST_DB_URL"]["description"]


def test_seed_maps_fields_to_columns_and_fills_python_defaults():
    plan = json.loads((PLANS / "two-entity.plan.json").read_text())
    spec = {"seed": [{"entity": "Project", "records": [{"name": "Alpha"}, {"id": "p-2", "name": "Beta"}]}]}

    blocks = build_seed(spec, plan, "gen_1", "2026-10-26T00:00:00+00:00")

    assert blocks[0]["table"] == "projects"
    first, second = blocks[0]["rows"]
    assert first["name"] == "Alpha" and first["created_at"] == "2026-10-26T00:00:00+00:00"
    assert len(first["id"]) == 36 and second["id"] == "p-2"
    assert build_seed(spec, plan, "gen_1", "x")[0]["rows"][0]["id"] == first["id"], "ids are deterministic"
