"""What the plugins write at scaffold time (Story 10.1): their files, `src/main.py` from the app-startup hook, their
settings in `src/configs/config.py` and `.env.ex`, their requirements. Applied by `scaffold_project`, so every project
has them on the template and the engine path alike; with no plan, the plugins every project has (the rate limiter)."""

from pathlib import Path
from typing import Any

from ..backend.pysource import Imports
from . import plan_plugins
from .base import Code, Plugin

SETTINGS_PLACEHOLDER = "    # {{PLUGIN_SETTINGS}}\n"
TEST_ENV_PLACEHOLDER = "# {{PLUGIN_TEST_ENV}}\n"


def main_file(plugins: list[Plugin], plan: dict[str, Any] | None) -> str:
    """`src/main.py`: routers in the lifespan, the plugins' setup, CORS, the access log, the exception handlers."""
    imports = (
        Imports()
        .add("contextlib", "asynccontextmanager")
        .add("fastapi", "FastAPI")
        .add("fastapi.exceptions", "RequestValidationError")
        .add("fastapi.middleware.cors", "CORSMiddleware")
        .add("src.configs", "config", "setup_logging")
        .add("src.libs.exceptions", "BaseException")
        .add("src.libs.exceptions.handlers", "base_exception_handler", "validation_exception_handler")
        .add("src.libs.middlewares", "AccessLogMiddleware")
        .add("src.routers", "all_router")
    )
    setup: list[str] = []
    handlers = ["app.add_exception_handler(BaseException, base_exception_handler)",
                "app.add_exception_handler(RequestValidationError, validation_exception_handler)"]  # fmt: skip
    lifespan = ["    for router in all_router:", "        app.include_router(router)"]
    for plugin in plugins:
        startup = plugin.app_startup(plan)
        if startup is None:
            continue
        for module, names in startup.imports:
            imports.add(module, *names)
        setup += startup.setup
        handlers += [f"app.add_exception_handler({error}, {handler})" for error, handler in startup.handlers]
        lifespan += [f"    {line}" for line in startup.lifespan]
    return (
        imports.render()
        + "\nsetup_logging()\n\n\n@asynccontextmanager\nasync def lifespan(app: FastAPI):\n"
        + "\n".join(lifespan)
        + "\n    yield\n\n\napp = FastAPI(title=config.app_name, lifespan=lifespan)\n"
        + "".join(f"{line}\n" for line in setup)
        + "app.add_middleware(\n    CORSMiddleware,\n    allow_origins=config.cors_origin_list,\n"
        '    allow_methods=["*"],\n    allow_headers=["*"],\n)\n'
        "app.add_middleware(AccessLogMiddleware)\n" + "".join(f"{line}\n" for line in handlers)
    )


def plugin_files(plan: dict[str, Any] | None) -> dict[str, str]:
    """Every file the plugins write (theirs, and `src/main.py`), by project-relative path."""
    plugins = plan_plugins(plan)
    files: dict[str, str] = {}
    for plugin in plugins:
        files |= plugin.files(plan)
    files["src/main.py"] = main_file(plugins, plan)
    return files


def owned_plugin_files(plan: dict[str, Any] | None) -> list[str]:
    """The plugins' files under the paths their `plugin.json` owns: generator-owned, the engine may not edit them
    (an integration stub, which someone must fill in, is not)."""
    owned = []
    for plugin in plan_plugins(plan):
        prefixes = tuple(plugin.meta.get("owns") or [])
        owned += [path for path in plugin.files(plan) if prefixes and path.startswith(prefixes)]
    return sorted([*owned, "src/main.py"])


def apply_plugins(project: Path, plan: dict[str, Any] | None) -> list[str]:
    """Writes the plugins' files into a scaffolded project and adds their settings and requirements to the
    overlay's files; returns the files written."""
    plugins = plan_plugins(plan)
    files = plugin_files(plan)
    for relative, text in files.items():
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    settings = [setting for plugin in plugins for setting in plugin.settings(plan)]
    config = project / "src/configs/config.py"
    if config.is_file():
        lines = "".join(
            f"    {s.name}: {s.annotation}" + (f" = {s.default}" if s.default is not None else "")
            + (f"  # {s.comment}" if s.comment else "") + "\n"
            for s in settings
        )  # fmt: skip
        config.write_text(config.read_text().replace(SETTINGS_PLACEHOLDER, lines))
    conftest = project / "tests/conftest.py"
    if conftest.is_file():
        tested = [s for s in settings if s.test_value is not None]
        lines = "".join(f'os.environ.setdefault("{s.name.upper()}", "{s.test_value}")\n' for s in tested)
        conftest.write_text(conftest.read_text().replace(TEST_ENV_PLACEHOLDER, lines))
    env = project / ".env.ex"
    examples = [s.example for s in settings if s.example is not None]
    if env.is_file() and examples:
        text = env.read_text()
        env.write_text(text + ("" if text.endswith("\n") else "\n") + "\n".join(examples) + "\n")
    requirements = project / "requirements.txt"
    if requirements.is_file():
        # Only what the base does not pin already: the sandbox's baked venv matches the base requirements exactly
        # (docker/runner), so the rate limiter's `slowapi`, in the base since 5.4, keeps every project on it.
        present = set(requirements.read_text().splitlines())
        extra = list(dict.fromkeys(line for plugin in plugins for line in plugin.requirements() if line not in present))
    if requirements.is_file() and extra:
        text = requirements.read_text()
        requirements.write_text(text + ("" if text.endswith("\n") else "\n") + "\n".join(extra) + "\n")
    return sorted(files)


def worker_startup(plan: dict[str, Any] | None) -> list[Code]:
    """What the generated job worker starts with, from each plugin's `worker_startup` (rendered by Story 10.6)."""
    return [code for plugin in plan_plugins(plan) if (code := plugin.worker_startup(plan)) is not None]
