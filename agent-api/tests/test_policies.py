"""The policies plugin (Story 10.3): role and ownership policies in the routes, use cases, repositories and tests;
the owner taken from the signed-in user; `allowedActions` per user; the contract's policies and scenarios."""

import json
from pathlib import Path

from src.orchestrator.backend.codegen import codegen_gaps, module_files, module_tests
from src.orchestrator.backend.planner import build_plan
from src.orchestrator.checks.smoke import scenario_calls
from src.orchestrator.integration.contract import build_contract, contract_operations
from src.orchestrator.plugins import extended_spec
from tests.generation_helpers import normalized

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


def policy_spec(tmp_path: Path, deny: int = 404) -> dict:
    """two-entity with JWT auth; tasks have an owner. get, update and list: the owner's (admins reach all); delete:
    admins only; create: any signed-in user, who becomes the owner."""
    raw = json.loads((EXAMPLES / "specs" / "two-entity.json").read_text())
    raw["auth"] = {"type": "jwt", "roles": ["member", "admin"]}
    task = next(entity for entity in raw["entities"] if entity["name"] == "Task")
    task["fields"].append({"name": "ownerId", "type": "uuid", "required": True})
    raw["policies"] = [
        {"name": "ownTasks", "type": "ownership", "ownerField": "ownerId", "bypassRoles": ["admin"],
         **({"denyStatus": deny} if deny != 404 else {})},
        {"name": "adminOnly", "type": "role", "roles": ["admin"]},
    ]  # fmt: skip
    for op in raw["operations"]:
        if op["operationId"] in ("task.get", "task.update", "task.list"):
            op["policy"] = "ownTasks"
        elif op["operationId"] == "task.delete":
            op["policy"] = "adminOnly"
        elif op["operationId"] == "task.create":
            op["auth"] = "jwt"
    (tmp_path / "policy-spec.json").write_text(json.dumps(raw))
    return normalized(tmp_path / "policy-spec.json")


def _tasks(plan: dict) -> dict:
    return next(module for module in plan["modules"] if module["name"] == "tasks")


def _files(tmp_path: Path, deny: int = 404) -> dict[str, str]:
    spec = policy_spec(tmp_path, deny)
    plan = build_plan(spec)
    return module_files(plan, extended_spec(spec), _tasks(plan)) | module_tests(plan, extended_spec(spec), _tasks(plan))


def test_policies_are_planned_and_no_longer_engine_gaps(tmp_path):
    plan = build_plan(policy_spec(tmp_path))
    tasks = _tasks(plan)
    assert {"name": "policies", "version": "1"} in plan["plugins"]
    assert codegen_gaps(tasks) == [] and plan["unresolved"] == []
    ops = {op["operationId"]: op for op in tasks["operations"]}
    assert ops["task.get"]["auth"]["ownership"] == {
        "field": "ownerId",
        "attr": "owner_id",
        "bypassRoles": ["admin"],
        "deny": 404,
    }
    assert ops["task.delete"]["auth"]["roles"] == ["admin"]
    assert {"status": 403, "exception": "ForbiddenException", "code": "FORBIDDEN"} in ops["task.delete"]["errors"]
    owner = next(c for m in plan["models"] if m["entity"] == "Task" for c in m["columns"] if c["attr"] == "owner_id")
    assert owner["source"] == "currentUser" and owner["foreignKey"]["references"] == "users.id"
    # a second plain demo user, so one member's record is out of another's reach
    assert [user["login"] for user in plan["auth"]["demoUsers"]] == [
        "demo-member@example.com",
        "demo-admin@example.com",
        "demo-member-2@example.com",
    ]


def test_a_role_policy_narrows_the_current_user_of_its_route(tmp_path):
    router = _files(tmp_path)["src/modules/tasks/presenter/router.py"]
    assert 'current_user: Annotated[UserEntity, Depends(require_roles("admin"))],' in router
    assert router.count("current_user: CurrentUserDep") == 4  # create, get, list, update (auth-jwt's, replaced)
    assert "await usecase.execute(id)\n" in router  # the role was checked; delete's use case needs no user


def test_ownership_is_checked_in_the_use_cases_and_scopes_the_list(tmp_path):
    files = _files(tmp_path)
    for name, record in (("get_task_usecase", "task"), ("update_task_usecase", "current")):
        usecase = files[f"src/modules/tasks/usecases/{name}.py"]
        assert f'if {record}.owner_id != current_user.id and current_user.role not in ("admin",):' in usecase
        assert 'raise NotFoundException("Task not found"' in usecase
    listing = files["src/modules/tasks/usecases/list_tasks_usecase.py"]
    assert 'owned_by = None if current_user.role in ("admin",) else current_user.id' in listing
    assert "offset, owned_by=owned_by)" in listing
    repository = files["src/modules/tasks/infrastructure/persistence/task_repository.py"]
    assert "        owned_by: uuid.UUID | None = None,\n" in repository
    assert "query = query.where(col(TaskModel.owner_id) == owned_by)" in repository
    assert all(len(line) <= 120 for text in files.values() for line in text.splitlines())


def test_another_users_record_can_answer_403(tmp_path):
    usecase = _files(tmp_path, deny=403)["src/modules/tasks/usecases/get_task_usecase.py"]
    assert 'raise ForbiddenException("This record belongs to another user")' in usecase


def test_create_takes_the_owner_from_the_signed_in_user(tmp_path):
    files = _files(tmp_path)
    dto = files["src/modules/tasks/presenter/dtos/create_task_dto.py"]
    assert "owner_id: uuid.UUID | None = Field(default=None, exclude=True)" in dto  # sent: ignored
    assert "def to_entity(self, owner_id: uuid.UUID) -> TaskEntity:" in dto
    assert "owner_id" not in files["src/modules/tasks/presenter/dtos/update_task_dto.py"]
    usecase = files["src/modules/tasks/usecases/create_task_usecase.py"]
    assert "self.task_repo.create(dto.to_entity(current_user.id))" in usecase
    repository = files["src/modules/tasks/infrastructure/persistence/task_repository.py"]
    assert 'details={"fields": ["projectId"]}' in repository  # the owner is not the client's reference


def test_allowed_actions_follow_the_callers_role_and_ownership(tmp_path):
    files = _files(tmp_path)
    dto = files["src/modules/tasks/presenter/dtos/task_response_dto.py"]
    assert '"update": user is not None and (entity.owner_id == user.id or user.role in ("admin",)),' in dto
    assert '"delete": user is not None and user.role in ("admin",),' in dto
    assert '"allowed_actions": allowed_actions(entity, user),' in dto
    for name in ("get_task_usecase", "update_task_usecase", "create_task_usecase"):
        assert "user=current_user)" in files[f"src/modules/tasks/usecases/{name}.py"]
    assert "references, user=current_user)" in files["src/modules/tasks/usecases/list_tasks_usecase.py"]


def test_the_generated_tests_cover_owner_other_user_bypass_and_missing_role(tmp_path):
    tests = _files(tmp_path)["tests/modules/tasks/test_task_api.py"]
    assert 'values["owner_id"] = current_user_id() or _seed_user().id' in tests  # the signed-in user owns seeds
    for name in (
        "test_get_task__other_owner",
        "test_update_task__other_owner",
        "test_get_task__bypass",
        "test_list_tasks__own_records",
        "test_delete_task__missing_role",
    ):
        assert f"def {name}(client):" in tests
    # delete's own tests sign in with the role it needs
    ok = tests.split("def test_delete_task__ok(client):\n")[1]
    assert ok.startswith('    client.headers["Authorization"] = f"Bearer {sign_in(client, role=\'admin\')}"\n')


def test_the_contract_carries_policies_owner_source_and_scenarios(tmp_path):
    contract = build_contract(policy_spec(tmp_path))
    ops = {op_id: found["operation"] for op_id, found in contract_operations(contract).items()}
    assert ops["task.get"]["x-bga"]["policy"] == {
        "name": "ownTasks",
        "type": "ownership",
        "ownerField": "ownerId",
        "bypassRoles": ["admin"],
        "deny": 404,
    }
    assert ops["task.delete"]["x-bga"]["policy"] == {"name": "adminOnly", "type": "role", "roles": ["admin"]}
    request = contract["components"]["schemas"]["CreateTaskRequest"]
    assert request["properties"]["ownerId"] == {"type": "string", "readOnly": True, "x-bga": {"source": "currentUser"}}
    assert "ownerId" not in request["required"]
    task = contract["x-bga"]["entities"]["Task"]
    assert task["ownerField"] == "ownerId"
    assert task["actionPolicies"] == {
        "update": {"ownerField": "ownerId", "bypassRoles": ["admin"]},
        "delete": {"roles": ["admin"]},
    }
    forbidden = next(e for e in ops["task.delete"]["x-bga"]["errors"] if e["status"] == 403)
    assert forbidden == {"status": 403, "code": "FORBIDDEN", "message": "Your role cannot do this"}

    calls, _ = scenario_calls(contract)
    by = {(call["operationId"], call["scenario"]): call for call in calls}
    other = by[("task.get", "another user's record")]
    assert other["user"] == "demo-member@example.com" and other["expect"] == {"status": 404, "code": "NOT_FOUND"}
    owner_of = {row["id"]: row["ownerId"] for row in contract["x-bga"]["fixtures"]["Task"]}
    member = contract["x-bga"]["fixtures"]["User"][0]
    assert owner_of[other["path"].rsplit("/", 1)[1]] != member["id"]
    assert by[("task.delete", "wrong role")]["user"] == "demo-member@example.com"
    assert by[("task.delete", "wrong role")]["expect"] == {"status": 403, "code": "FORBIDDEN"}
    assert by[("task.delete", "unknown id")]["user"] == "demo-admin@example.com"  # the role it needs
    assert "user" not in by[("task.get", "success")]  # the default demo user owns the first task


def test_previews_seed_the_owners_before_their_records(tmp_path):
    """The user entity comes last in the spec (auth-jwt adds it) but owns tasks: its rows are seeded first."""
    from src.orchestrator.packaging import build_contract_seed

    spec = policy_spec(tmp_path)
    plan = build_plan(spec)
    tables = [block["table"] for block in build_contract_seed(build_contract(spec, plan), plan)]
    assert tables.index("users") < tables.index("tasks") and tables.index("projects") < tables.index("tasks")
