"""The auth-jwt plugin (Story 10.2): the user entity and demo users, the plugin's own module, protected routes,
the contract's auth operations and scenarios, and what the smoke check does with them."""

import json
from pathlib import Path

from src.orchestrator.backend.codegen import codegen_gaps, database_files, module_files, module_tests, routers_file
from src.orchestrator.backend.planner import build_plan
from src.orchestrator.backend.scaffold import scaffold_project
from src.orchestrator.checks.smoke import smoke_calls, smoke_login
from src.orchestrator.integration.contract import build_contract, contract_operations, presented_record
from src.orchestrator.plugins.auth_jwt import DEMO_HASH, DEMO_PASSWORD
from tests.generation_helpers import TEMPLATE, normalized

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


def auth_spec(tmp_path: Path, roles: list[str] | None = None) -> dict:
    """two-entity with JWT auth on every task operation (projects stay public)."""
    raw = json.loads((EXAMPLES / "specs" / "two-entity.json").read_text())
    raw["auth"] = {"type": "jwt", "roles": roles if roles is not None else ["member", "admin"]}
    for op in raw["operations"]:
        if op["operationId"].startswith("task."):
            op["auth"] = "jwt"
    (tmp_path / "auth-spec.json").write_text(json.dumps(raw))
    return normalized(tmp_path / "auth-spec.json")


def _ops(contract: dict) -> dict:
    return {op_id: found["operation"] for op_id, found in contract_operations(contract).items()}


def test_the_user_entity_is_added_with_a_secret_password_hash_and_demo_users(tmp_path):
    plan = build_plan(auth_spec(tmp_path))
    user = next(model for model in plan["models"] if model.get("entity") == "User")
    columns = {column["apiName"]: column for column in user["columns"]}
    assert columns["email"]["unique"] and columns["passwordHash"]["secret"]
    assert columns["role"]["enum"]["values"] == ["member", "admin"]
    assert plan["auth"]["demoUsers"] == [
        {"login": "demo-member@example.com", "password": DEMO_PASSWORD, "role": "member"},
        {"login": "demo-admin@example.com", "password": DEMO_PASSWORD, "role": "admin"},
    ]
    assert {"name": "auth-jwt", "version": "1"} in plan["plugins"]
    assert plan["routers"]["order"][:2] == ["health_router", "auth_router"]


def test_the_auth_module_is_the_plugins_and_jwt_is_no_longer_an_engine_gap(tmp_path):
    plan = build_plan(auth_spec(tmp_path))
    auth = next(module for module in plan["modules"] if module["name"] == "auth")
    assert auth["plugin"] == "auth-jwt" and codegen_gaps(auth) == []
    tasks = next(module for module in plan["modules"] if module["name"] == "tasks")
    assert codegen_gaps(tasks) == []  # `auth: jwt` is the plugin's; a policy would still be the engine's (10.3)
    assert not [entry for entry in plan["unresolved"] if entry["kind"] == "auth"]


def test_protected_routes_take_the_current_user_and_their_tests_sign_in(tmp_path):
    spec = auth_spec(tmp_path)
    plan = build_plan(spec)
    tasks = next(module for module in plan["modules"] if module["name"] == "tasks")
    router = module_files(plan, spec, tasks)["src/modules/tasks/presenter/router.py"]
    assert router.count("current_user: CurrentUserDep") == 5
    assert "from src.libs.security import CurrentUserDep" in router
    projects = next(module for module in plan["modules"] if module["name"] == "projects")
    assert "CurrentUserDep" not in module_files(plan, spec, projects)["src/modules/projects/presenter/router.py"]
    tests = module_tests(plan, spec, tasks)["tests/modules/tasks/test_task_api.py"]
    assert 'client.headers["Authorization"] = f"Bearer {sign_in(client)}"' in tests


def test_the_password_hash_never_reaches_a_request_or_a_response(tmp_path):
    spec = auth_spec(tmp_path)
    plan = build_plan(spec)
    contract = build_contract(spec, plan)
    schemas = contract["components"]["schemas"]
    assert "passwordHash" not in schemas["Account"]["properties"]
    assert "passwordHash" not in schemas["RegisterRequest"]["properties"]
    assert set(schemas["RegisterRequest"]["required"]) == {"email", "password"}
    fixtures = contract["x-bga"]["fixtures"]["User"]
    assert all(row["passwordHash"] == DEMO_HASH for row in fixtures)  # the seed signs the demo users in
    assert "passwordHash" not in presented_record(contract, "User", fixtures[0])


def test_the_contract_carries_the_auth_operations_and_a_401_per_protected_operation(tmp_path):
    contract = build_contract(auth_spec(tmp_path))
    ops = _ops(contract)
    assert contract["components"]["securitySchemes"]["bearerAuth"]["scheme"] == "bearer"
    assert ops["auth.me"]["security"] == [{"bearerAuth": []}]
    assert [s["name"] for s in ops["auth.register"]["x-bga"]["scenarios"]] == [
        "success",
        "duplicate email",
        "missing password",
    ]
    assert [s["name"] for s in ops["auth.login"]["x-bga"]["scenarios"]] == ["success", "wrong password"]
    for op_id in ("task.create", "task.get", "task.list", "task.update", "task.delete"):
        first = ops[op_id]["x-bga"]["scenarios"][0]
        assert first["name"] == "no token" and first["auth"] is False
        assert first["expect"] == {"status": 401, "code": "UNAUTHORIZED"}
    assert "security" not in ops["project.get"]


def test_the_smoke_check_signs_in_as_a_demo_user(tmp_path):
    spec = auth_spec(tmp_path)
    contract, plan = build_contract(spec), build_plan(spec)
    assert smoke_login(contract) == {
        "operationId": "auth.login",
        "path": "/auth/login",
        "body": {"email": "demo-member@example.com", "password": DEMO_PASSWORD},
    }
    calls, skipped = smoke_calls(contract, plan)
    assert skipped == []
    task_get = [call for call in calls if call["operationId"] == "task.get"]
    assert [(call["scenario"], call["auth"]) for call in task_get] == [
        ("no token", False),
        ("success", True),
        ("unknown id", True),
    ]


def test_the_project_has_the_security_library_settings_and_tests(tmp_path):
    spec = auth_spec(tmp_path, roles=[])
    plan = build_plan(spec)
    project = tmp_path / "project"
    project.mkdir()
    scaffold_project(TEMPLATE, project, "Auth Tracker", plan=plan)
    files = database_files(plan) | {"src/routers.py": routers_file(plan)}
    for relative, text in files.items():
        (project / relative).parent.mkdir(parents=True, exist_ok=True)
        (project / relative).write_text(text)
    config = (project / "src/configs/config.py").read_text()
    assert "    jwt_secret: str  # from the environment only\n" in config
    assert "access_token_expire_minutes: int = 60" in config
    env = (project / ".env.ex").read_text()
    assert "JWT_SECRET=\n" in env and "ACCESS_TOKEN_EXPIRE_MINUTES=60\n" in env
    assert 'os.environ.setdefault("JWT_SECRET",' in (project / "tests/conftest.py").read_text()
    assert (project / "requirements.txt").read_text().endswith("pyjwt==2.15.1\npwdlib[argon2]==0.3.1\n")
    router = (project / "src/modules/auth/presenter/router.py").read_text()
    assert router.count("@limiter.limit(config.auth_rate_limit)") == 2
    assert "auth_router" in (project / "src/routers.py").read_text()
    user = next(model for model in plan["models"] if model.get("entity") == "User")
    assert {column["apiName"] for column in user["columns"]} >= {"role"}  # no roles: a plain `role`, default user
    for path in [*(project / "src").rglob("*.py"), *(project / "tests").rglob("*.py")]:
        compile(path.read_text(), str(path), "exec")


def test_previews_seed_a_demo_user_per_role(tmp_path):
    """A backend-only preview seeds from the spec; the raw spec has no seed, the plugin's demo users still come."""
    from src.orchestrator.packaging import build_seed

    spec = auth_spec(tmp_path)
    assert not spec.get("seed")
    blocks = build_seed(spec, build_plan(spec), "gen_test", "2026-01-15T09:00:00+00:00")
    [users] = [block for block in blocks if block["table"] == "users"]
    assert [(row["email"], row["role"]) for row in users["rows"]] == [
        ("demo-member@example.com", "member"),
        ("demo-admin@example.com", "admin"),
    ]
    assert all(row["password_hash"] == DEMO_HASH for row in users["rows"])
