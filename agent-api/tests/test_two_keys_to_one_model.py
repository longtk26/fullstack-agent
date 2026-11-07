"""Two foreign keys from one entity to the same parent (a request's reporter and its assignee, both people; Epic 25
makes this common: an owner and an assigned worker are both users). Each relationship is named after its key and says
which key it follows, so SQLAlchemy can map both sides; a pair linked once keeps today's names."""

import json
import subprocess
import sys
from pathlib import Path

from src.modules.shared.domain.backend_spec import validate_spec_data
from src.orchestrator.backend.codegen import model_file
from src.orchestrator.backend.planner import build_plan

SPEC = {
    "specVersion": "1.0",
    "project": {"name": "Desk", "description": "Requests reported by one person and handled by another"},
    "stack": {"framework": "fastapi", "database": "postgresql", "orm": "sqlalchemy", "migration": "alembic"},
    "entities": [
        {"name": "Person", "fields": [{"name": "id", "type": "uuid", "primary": True},
                                     {"name": "name", "type": "string", "required": True}]},
        {"name": "Team", "fields": [{"name": "id", "type": "uuid", "primary": True},
                                   {"name": "name", "type": "string", "required": True}]},
        {"name": "Ticket", "fields": [{"name": "id", "type": "uuid", "primary": True},
                                     {"name": "title", "type": "string", "required": True},
                                     {"name": "reporterId", "type": "uuid", "required": True},
                                     {"name": "assigneeId", "type": "uuid"},
                                     {"name": "teamId", "type": "uuid", "required": True}]},
    ],
    "relationships": [
        {"name": "reportedTickets", "type": "one-to-many", "from": "Person", "to": "Ticket", "foreignKey": "reporterId",
         "onDelete": "CASCADE"},
        {"name": "assignedTickets", "type": "one-to-many", "from": "Person", "to": "Ticket", "foreignKey": "assigneeId",
         "onDelete": "SET NULL"},
        {"name": "teamTickets", "type": "one-to-many", "from": "Team", "to": "Ticket", "foreignKey": "teamId",
         "onDelete": "CASCADE"},
    ],
    "operations": [],
}  # fmt: skip


def _models(tmp_path: Path) -> dict[str, str]:
    result = validate_spec_data(json.loads(json.dumps(SPEC)))
    assert result.normalized is not None, [issue.message for issue in result.report.errors]
    plan = build_plan(result.normalized)
    files = {}
    for model in plan["models"]:
        if model["entity"] in ("Person", "Team", "Ticket"):
            files[model["class"]] = model_file(model, plan)
    return files


def test_each_relationship_is_named_after_its_key(tmp_path):
    files = _models(tmp_path)
    ticket, person, team = files["TicketModel"], files["PersonModel"], files["TeamModel"]
    assert 'reporter: "PersonModel" = Relationship(back_populates="tickets_as_reporter", ' in ticket
    assert '"foreign_keys": "[TicketModel.reporter_id]"' in ticket
    assert 'assignee: "PersonModel" = Relationship(back_populates="tickets_as_assignee", ' in ticket
    reporter_side = 'tickets_as_reporter: list["TicketModel"] = Relationship(back_populates="reporter", '
    assert reporter_side + 'passive_deletes="all", ' in person
    assert '"foreign_keys": "[TicketModel.assignee_id]"' in person
    # linked once: today's names, no foreign_keys
    assert 'team: "TeamModel" = Relationship(back_populates="tickets")\n' in ticket
    assert 'tickets: list["TicketModel"] = Relationship(back_populates="team", passive_deletes="all")' in team


def test_sqlalchemy_maps_both_keys(tmp_path):
    """The generated models import and configure (what failed in a generated backend: login and register were 500)."""
    package = tmp_path / "models"
    package.mkdir()
    (package / "__init__.py").write_text("")
    names = []
    for name, source in _models(tmp_path).items():
        module = name.removesuffix("Model").lower() + "_model"
        (package / f"{module}.py").write_text(source)
        names.append(module)
    script = (
        "import importlib, sqlalchemy.orm\n"
        + "".join(f"importlib.import_module('models.{n}')\n" for n in names)
        + "sqlalchemy.orm.configure_mappers()\nprint('mapped')\n"
    )
    run = subprocess.run([sys.executable, "-c", script], cwd=tmp_path, capture_output=True, text=True, timeout=60)
    assert run.returncode == 0 and "mapped" in run.stdout, run.stderr[-2000:]
