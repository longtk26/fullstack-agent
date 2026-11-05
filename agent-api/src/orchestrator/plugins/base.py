"""The shape of a generation-time backend plugin (Story 10.1, decisions P1 and P2).

A plugin writes plain fastapi-skills source into the generated project (its `templates/plugins/<name>/backend/files`)
and connects it to the generated code through six named hook points; nothing of ours runs in the generated app. Every
hook is a pure function of (spec, plan, module, operation), so codegen stays byte-identical between runs. A hook that
contributes nothing leaves the generated code exactly as it was without plugins.

| Hook | Where it lands |
|---|---|
| `router_params` | route handler parameters (a dependency such as the current user), passed to the use case |
| `prechecks` | lines at the start of a use case, after the record is loaded (an ownership check, a rule) |
| `events` | lines right after a use case's write, in the same transaction (an outbox event) |
| `repository_filters` | an optional parameter of the repository's `list` and the `where` it adds |
| `response_fields` | fields of a record's response DTO and how they are computed |
| `app_startup` | imports, middleware, exception handlers and lifespan lines of `src/main.py` |
| `worker_startup` | what the generated job worker starts with (rendered by 10.6) |
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PLUGINS_DIR = Path(__file__).resolve().parents[3] / "templates" / "plugins"

# An import: `(module, names)`; no names is `import module`.
Import = tuple[str, tuple[str, ...]]


@dataclass(frozen=True)
class RouterParam:
    """A route handler parameter (`current_user: CurrentUserDep`), given to the use case as `usecase_annotation`."""

    name: str
    annotation: str
    usecase_annotation: str | None = None  # None: the use case does not take it
    imports: tuple[Import, ...] = ()
    usecase_imports: tuple[Import, ...] = ()


@dataclass(frozen=True)
class Code:
    """Lines of code (without the block's indentation) and the imports they need."""

    lines: tuple[str, ...]
    imports: tuple[Import, ...] = ()


@dataclass(frozen=True)
class RepositoryFilter:
    """`list(..., <param>: <annotation> = None)` adds `query.where(<condition>)` when given; the list use case passes
    `<param>=<value>`. `condition` may use the model class as `{model}`."""

    param: str
    annotation: str
    condition: str
    value: str
    imports: tuple[Import, ...] = ()


@dataclass(frozen=True)
class ResponseField:
    """A response DTO field and its value, an expression of `entity` (and `refs`, the parents' labels)."""

    attr: str
    annotation: str
    value: str
    imports: tuple[Import, ...] = ()


@dataclass(frozen=True)
class AppStartup:
    """What a plugin adds to `src/main.py`: imports, statements after `app = FastAPI(...)` (state, middleware; they run
    before CORS and the access log are added), exception handlers, and lines in the lifespan before `yield`."""

    imports: tuple[Import, ...] = ()
    setup: tuple[str, ...] = ()
    handlers: tuple[tuple[str, str], ...] = ()  # (exception class, handler function)
    lifespan: tuple[str, ...] = ()


@dataclass(frozen=True)
class Setting:
    """A `Config` field of the generated app (env var = the upper-case name) and its `.env.ex` line."""

    name: str
    annotation: str
    default: str | None  # a Python literal; None: required, from the environment only
    comment: str | None = None
    example: str | None = None  # the `.env.ex` value; None: not listed
    test_value: str | None = None  # set in `tests/conftest.py` before the app loads; None: left to the environment


@dataclass
class Plugin:
    """A plugin's code: subclasses override what they contribute. `name` matches `templates/plugins/<name>/`."""

    name: str = ""
    requires: tuple[str, ...] = field(default=())
    # Applies to every project (the rate limiter): also active when there is no plan (`scaffold_project` alone).
    always: bool = False

    # -- what it is ---------------------------------------------------------------------------------------------------

    @property
    def folder(self) -> Path:
        return PLUGINS_DIR / self.name

    @property
    def meta(self) -> dict[str, Any]:
        return json.loads((self.folder / "plugin.json").read_text())

    @property
    def version(self) -> str:
        return self.meta["version"]

    def applies(self, spec: dict[str, Any]) -> bool:
        return self.always

    # -- plan, contract, files ----------------------------------------------------------------------------------------

    def plan(self, plan: dict[str, Any], spec: dict[str, Any]) -> None:
        """Adds modules, operations or unresolved entries to the plan (in place)."""

    def contract(self, contract: dict[str, Any], plan: dict[str, Any], spec: dict[str, Any]) -> None:
        """Adds what the plugin answers to the contract (in place): schemas, errors, scenarios."""

    def files(self, plan: dict[str, Any] | None) -> dict[str, str]:
        """The backend files it copies into the project (`backend/files/**`), owned by the generator."""
        root = self.folder / "backend" / "files"
        return {
            path.relative_to(root).as_posix(): path.read_text()
            for path in sorted(root.rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts
        }

    def requirements(self) -> list[str]:
        return list(self.meta.get("requirements", []))

    def settings(self, plan: dict[str, Any] | None) -> list[Setting]:
        return []

    # -- hooks (Story 10.1, P2) ---------------------------------------------------------------------------------------

    def router_params(self, plan: dict[str, Any], module: dict[str, Any], op: dict[str, Any]) -> list[RouterParam]:
        return []

    def prechecks(
        self, plan: dict[str, Any], module: dict[str, Any], op: dict[str, Any], record: str | None
    ) -> list[Code]:
        """`record`: the variable holding the loaded record (get, update, delete), or None (create, list)."""
        return []

    def events(self, plan: dict[str, Any], module: dict[str, Any], op: dict[str, Any], record: str) -> list[Code]:
        return []

    def repository_filters(self, plan: dict[str, Any], module: dict[str, Any]) -> list[RepositoryFilter]:
        return []

    def response_fields(self, plan: dict[str, Any], module: dict[str, Any]) -> list[ResponseField]:
        return []

    def app_startup(self, plan: dict[str, Any] | None) -> AppStartup | None:
        return None

    def worker_startup(self, plan: dict[str, Any] | None) -> Code | None:
        return None

    def test_setup(self, plan: dict[str, Any], module: dict[str, Any]) -> Code | None:
        """Module-level code of a module's generated test file (a fixture that signs the client in)."""
        return None

    # -- what it tells -------------------------------------------------------------------------------------------------

    def smoke(self, contract: dict[str, Any], plan: dict[str, Any]) -> list[dict[str, Any]]:
        """Extra smoke calls (shaped like `checks.smoke` scenario calls) proving its API works."""
        return []

    def extend_spec(self, spec: dict[str, Any]) -> None:
        """Adds to a copy of the spec, before planning, what the plugin needs (an entity, fields, seed records)."""

    def owns_module(self, module: dict[str, Any]) -> bool:
        """A plan module the plugin writes itself (`module["plugin"]`): codegen and the engine leave it alone."""
        return module.get("plugin") == self.name

    def manifest(self) -> dict[str, Any]:
        return {"name": self.name, "version": self.version}

    def engine_note(self, plan: dict[str, Any]) -> str | None:
        """What the `complete_backend` engine is told this project already has (18.13's context pack)."""
        return None
