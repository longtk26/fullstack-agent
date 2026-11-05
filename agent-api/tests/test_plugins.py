"""The plugin framework (Story 10.1): the registry and its order, the six hook points, the rate limiter as a plugin,
the integration stubs, and what the engine is told."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from src.orchestrator.backend.codegen import module_files
from src.orchestrator.backend.completion import module_context
from src.orchestrator.backend.planner import build_plan
from src.orchestrator.backend.scaffold import scaffold_project
from src.orchestrator.plugins import (
    REGISTRY,
    AppStartup,
    Code,
    Plugin,
    PluginError,
    RepositoryFilter,
    ResponseField,
    RouterParam,
    Setting,
    active_plugins,
    ordered,
)
from src.orchestrator.plugins.app import main_file, plugin_files, worker_startup
from tests.generation_helpers import TEMPLATE, normalized

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
TWO_ENTITY = json.loads((EXAMPLES / "specs" / "two-entity.json").read_text())


class HookProbePlugin(Plugin):
    """Test double (docs/development/test-doubles.md): contributes to every hook point of the `tasks` module, so the
    tests see each one land where it should."""

    def __init__(self, name: str = "hook-probe", requires: tuple[str, ...] = ()) -> None:
        super().__init__(name=name, requires=requires)

    @property
    def meta(self) -> dict[str, Any]:
        return {"name": self.name, "version": "0.1", "requirements": ["probe-lib==1.0"]}

    def applies(self, spec: dict[str, Any]) -> bool:
        return bool(spec.get("x-probe"))

    def files(self, plan: dict[str, Any] | None) -> dict[str, str]:
        return {"src/libs/probe/__init__.py": "def note(*args):\n    return args\n\n\nclass Caller:\n    id = 0\n"}

    def settings(self, plan: dict[str, Any] | None) -> list[Setting]:
        return [Setting("probe_key", "str", None, comment="from the environment", example="PROBE_KEY=")]

    def router_params(self, plan, module, op) -> list[RouterParam]:
        if module["name"] != "tasks":
            return []
        return [RouterParam("caller", "CallerDep", "Caller", (("src.libs.probe", ("CallerDep",)),),
                            (("src.libs.probe", ("Caller",)),))]  # fmt: skip

    def prechecks(self, plan, module, op, record) -> list[Code]:
        if module["name"] != "tasks":
            return []
        return [Code((f"note('precheck', {record or 'None'}, caller)",), (("src.libs.probe", ("note",)),))]

    def events(self, plan, module, op, record) -> list[Code]:
        if module["name"] != "tasks":
            return []
        return [Code((f"note('event', {record})",), (("src.libs.probe", ("note",)),))]

    def repository_filters(self, plan, module) -> list[RepositoryFilter]:
        if module["name"] != "tasks":
            return []
        return [RepositoryFilter("owner", "int | None", "col({model}.priority) == owner", "caller.id")]

    def response_fields(self, plan, module) -> list[ResponseField]:
        if module["name"] != "tasks":
            return []
        return [ResponseField("probe", "str", '"probed"')]

    def app_startup(self, plan) -> AppStartup:
        return AppStartup(
            imports=(("src.libs.probe", ("note",)),), setup=("note('setup')",), lifespan=("note('lifespan')",)
        )

    def worker_startup(self, plan) -> Code:
        return Code(("note('worker')",))


def _probe_spec() -> dict:
    spec = normalized(EXAMPLES / "specs" / "two-entity.json")
    spec["x-probe"] = True
    return spec


@pytest.fixture
def probe(monkeypatch):
    plugin = HookProbePlugin()
    monkeypatch.setitem(REGISTRY, plugin.name, plugin)
    return plugin


# -- registry --------------------------------------------------------------------------------------------------------


def test_every_plan_names_its_plugins_and_versions():
    plan = build_plan(normalized(EXAMPLES / "specs" / "two-entity.json"))
    assert plan["plugins"] == [{"name": "rate-limit", "version": "1"}]


def test_plugins_are_ordered_by_what_they_need(monkeypatch):
    first, second = HookProbePlugin("needs-base", requires=("base-probe",)), HookProbePlugin("base-probe")
    monkeypatch.setitem(REGISTRY, first.name, first)
    monkeypatch.setitem(REGISTRY, second.name, second)
    assert [p.name for p in ordered([first, second])] == ["base-probe", "needs-base"]

    monkeypatch.setitem(REGISTRY, "base-probe", HookProbePlugin("base-probe", requires=("needs-base",)))
    with pytest.raises(PluginError, match="cycle"):
        ordered([REGISTRY["needs-base"], REGISTRY["base-probe"]])
    with pytest.raises(PluginError, match="not registered"):
        ordered([HookProbePlugin("lonely", requires=("missing",))])


def test_a_plugin_needing_an_unknown_one_is_a_planner_error(monkeypatch):
    monkeypatch.setitem(REGISTRY, "lonely", HookProbePlugin("lonely", requires=("missing",)))
    with pytest.raises(PluginError):
        build_plan(_probe_spec())


# -- the rate limiter as a plugin ------------------------------------------------------------------------------------


def test_the_rate_limiter_is_a_plugin_every_project_has(tmp_path):
    scaffold_project(TEMPLATE, tmp_path, "X")  # no plan: the plugins every project has
    main = (tmp_path / "src/main.py").read_text()
    assert "app.add_middleware(SlowAPIMiddleware)" in main
    assert "app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)" in main
    assert (tmp_path / "src/libs/rate_limit/limiter.py").is_file()
    assert (tmp_path / "src/libs/rate_limit/handlers.py").is_file()
    config = (tmp_path / "src/configs/config.py").read_text()
    assert 'rate_limit_default: str = "120/minute"' in config and "PLUGIN_SETTINGS" not in config
    assert (tmp_path / "requirements.txt").read_text().count("slowapi==0.1.9") == 1  # in the base already
    for relative in ("src/main.py", "src/libs/rate_limit/handlers.py", "src/configs/config.py"):
        compile((tmp_path / relative).read_text(), relative, "exec")


def test_a_plans_plugins_are_scaffolded(tmp_path, probe):
    plan = build_plan(_probe_spec())
    info = scaffold_project(TEMPLATE, tmp_path, "X", plan=plan)
    assert info["plugins"] == [{"name": "rate-limit", "version": "1"}, {"name": "hook-probe", "version": "0.1"}]
    assert (tmp_path / "src/libs/probe/__init__.py").is_file()
    assert "    probe_key: str  # from the environment\n" in (tmp_path / "src/configs/config.py").read_text()
    assert (tmp_path / ".env.ex").read_text().endswith("PROBE_KEY=\n")
    assert (tmp_path / "requirements.txt").read_text().endswith("slowapi==0.1.9\nprobe-lib==1.0\n")


# -- the six hook points ---------------------------------------------------------------------------------------------


def test_each_hook_point_lands_where_it_should(probe):
    spec = _probe_spec()
    plan = build_plan(spec)
    tasks = next(module for module in plan["modules"] if module["name"] == "tasks")
    files = module_files(plan, spec, tasks)
    router = files["src/modules/tasks/presenter/router.py"]
    assert "caller: CallerDep" in router and "from src.libs.probe import CallerDep" in router
    assert "usecase.execute(id, body, caller)" in router  # update: path, body, then the plugin's argument
    create = files["src/modules/tasks/usecases/create_task_usecase.py"]
    assert "async def execute(self, dto: CreateTaskRequestDto, caller: Caller) -> TaskResponseDto:" in create
    assert create.index("note('precheck', None, caller)") < create.index(".create(dto.to_entity())")
    assert create.index(".create(dto.to_entity())") < create.index("note('event', task)")
    update = files["src/modules/tasks/usecases/update_task_usecase.py"]
    assert update.index("if current is None:") < update.index("note('precheck', current, caller)")
    delete = files["src/modules/tasks/usecases/delete_task_usecase.py"]
    assert "existing = self.task_repo.find_by_id(task_id)" in delete and "note('event', existing)" in delete
    repository = files["src/modules/tasks/infrastructure/persistence/task_repository.py"]
    assert "offset: int, owner: int | None = None" in repository
    assert (
        "        if owner is not None:\n            query = query.where(col(TaskModel.priority) == owner)" in repository
    )
    assert ", owner: int | None = None" in files["src/modules/tasks/ports/output/task_repository.py"]
    listed = files["src/modules/tasks/usecases/list_tasks_usecase.py"]
    assert "limit, offset, owner=caller.id)" in listed
    dto = files["src/modules/tasks/presenter/dtos/task_response_dto.py"]
    assert "    probe: str\n" in dto and '"probe": "probed"' in dto
    for relative, source in files.items():
        compile(source, relative, "exec")

    main = main_file(active_plugins(spec), plan)
    assert "note('setup')\napp.add_middleware(\n    CORSMiddleware" in main
    assert "        app.include_router(router)\n    note('lifespan')\n    yield" in main
    assert [code.lines for code in worker_startup(plan)] == [("note('worker')",)]


def test_a_later_plugin_replaces_a_route_parameter_of_the_same_name(probe, monkeypatch):
    """Story 10.3: `policies` narrows auth-jwt's `current_user` this way; here a second probe narrows `caller`."""

    class NarrowingProbe(HookProbePlugin):
        def router_params(self, plan, module, op) -> list[RouterParam]:
            if module["name"] != "tasks" or op["action"] != "delete":
                return []
            return [RouterParam("caller", "AdminCallerDep", None, (("src.libs.probe", ("AdminCallerDep",)),))]

    narrowing = NarrowingProbe("narrowing-probe", requires=("hook-probe",))
    monkeypatch.setitem(REGISTRY, narrowing.name, narrowing)
    spec = _probe_spec()
    plan = build_plan(spec)
    tasks = next(module for module in plan["modules"] if module["name"] == "tasks")
    router = module_files(plan, spec, tasks)["src/modules/tasks/presenter/router.py"]
    assert router.count("caller: AdminCallerDep") == 1 and router.count("caller: CallerDep") == 4
    assert "await usecase.execute(id)\n" in router  # the replacement does not pass it to the use case


def test_a_module_no_plugin_touches_is_unchanged(probe):
    spec = _probe_spec()
    plain_spec = normalized(EXAMPLES / "specs" / "two-entity.json")
    with_probe, without = build_plan(spec), build_plan(plain_spec)
    projects = next(m for m in with_probe["modules"] if m["name"] == "projects")
    plain = next(m for m in without["modules"] if m["name"] == "projects")
    assert module_files(with_probe, spec, projects) == module_files(without, plain_spec, plain)


# -- integrations without a plugin, and the engine's note ------------------------------------------------------------


def test_an_integration_without_a_plugin_gets_a_port_a_stub_and_an_unresolved_entry(tmp_path):
    raw = copy.deepcopy(TWO_ENTITY)
    raw["integrations"] = [{"name": "smsGateway", "description": "Sends text messages."}]
    (tmp_path / "spec.json").write_text(json.dumps(raw))
    plan = build_plan(normalized(tmp_path / "spec.json"))
    assert {"name": "integration-stubs", "version": "1"} in plan["plugins"]
    [entry] = [e for e in plan["unresolved"] if e["ref"] == "smsGateway"]
    assert entry["kind"] == "integration" and entry["specPath"] == "/integrations/0"
    assert "src/modules/integrations/infrastructure/adapters/sms_gateway_adapter.py" in entry["message"]

    project = tmp_path / "project"
    project.mkdir()
    scaffold_project(TEMPLATE, project, "X", plan=plan)
    adapter = (project / "src/modules/integrations/infrastructure/adapters/sms_gateway_adapter.py").read_text()
    assert 'raise NotImplementedError("sms_gateway: not implemented yet (stub adapter)")' in adapter
    assert "ISmsGatewayPortDep = Annotated[ISmsGatewayPort, Depends(SmsGatewayAdapter)]" in adapter
    assert 'sms_gateway_api_key: str = ""' in (project / "src/configs/config.py").read_text()
    assert (project / ".env.ex").read_text().endswith("SMS_GATEWAY_BASE_URL=\nSMS_GATEWAY_API_KEY=\n")
    for path in (project / "src/modules/integrations").rglob("*.py"):
        compile(path.read_text(), str(path), "exec")


def test_the_engine_is_told_what_the_plugins_wrote(tmp_path):
    spec = normalized(EXAMPLES / "specs" / "flashcards.json")
    plan = build_plan(spec)
    cards = next(module for module in plan["modules"] if module["name"] == "cards")
    pack = module_context(tmp_path, plan, spec, None, cards, [])
    assert "## Already in this project (read only)" in pack
    assert '`@limiter.limit("5/minute")`' in pack


def test_plugin_files_are_what_the_scaffold_writes(tmp_path):
    scaffold_project(TEMPLATE, tmp_path, "X")
    for relative, text in plugin_files(None).items():
        assert (tmp_path / relative).read_text() == text
