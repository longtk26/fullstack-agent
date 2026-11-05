"""Generation-time backend plugins (Story 10.1): the registry, which plugins a spec turns on, and their order.

Adding a plugin is a `templates/plugins/<name>/` folder (`plugin.json`, `backend/files/**`, later `frontend/files/**`)
and one `Plugin` subclass registered here; codegen calls the hooks of the plugins the plan names (`plan["plugins"]`).
"""

import copy
from typing import Any

from .auth_jwt import AuthJwtPlugin
from .base import (
    PLUGINS_DIR,
    ActionCheck,
    AppStartup,
    CaseContext,
    Code,
    Import,
    Plugin,
    RepositoryFilter,
    RepositoryMethod,
    ResponseField,
    RouterParam,
    Setting,
)
from .integrations import IntegrationStubsPlugin
from .jobs import JobsPlugin
from .policies import PoliciesPlugin
from .rate_limit import RateLimitPlugin
from .rules import RulesPlugin
from .storage import StoragePlugin

# Every plugin the generator knows, by name. Tests add their own with `monkeypatch.setitem(REGISTRY, ...)`.
REGISTRY: dict[str, Plugin] = {
    plugin.name: plugin
    for plugin in (
        RateLimitPlugin(),
        AuthJwtPlugin(),
        PoliciesPlugin(),
        RulesPlugin(),
        StoragePlugin(),
        JobsPlugin(),
        IntegrationStubsPlugin(),
    )
}


class PluginError(ValueError):
    """A plugin needs one that is not registered, or plugins need each other in a cycle (a planner error)."""


def ordered(plugins: list[Plugin]) -> list[Plugin]:
    """Dependencies first, else in registry order (so the output never depends on the spec's order)."""
    position = {name: index for index, name in enumerate(REGISTRY)}
    by_name = {plugin.name: plugin for plugin in plugins}
    out: list[Plugin] = []
    visiting: set[str] = set()

    def visit(plugin: Plugin) -> None:
        if plugin in out:
            return
        if plugin.name in visiting:
            raise PluginError(f"plugins need each other in a cycle: {plugin.name}")
        visiting.add(plugin.name)
        for name in plugin.requires:
            if name not in REGISTRY:
                raise PluginError(f"plugin '{plugin.name}' needs '{name}', which is not registered")
            visit(by_name.get(name) or REGISTRY[name])
        visiting.discard(plugin.name)
        out.append(plugin)

    for plugin in sorted(plugins, key=lambda p: position.get(p.name, len(position))):
        visit(plugin)
    return out


def active_plugins(spec: dict[str, Any]) -> list[Plugin]:
    """The plugins this spec turns on, with what they need, in order."""
    return ordered([plugin for plugin in REGISTRY.values() if plugin.applies(spec)])


def extended_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """A copy of the spec with what the active plugins add before planning (Story 10.2: the user entity, demo users).
    The planner, the contract and the seeds all read it; applying it twice changes nothing."""
    extending = [p for p in active_plugins(spec) if type(p).extend_spec is not Plugin.extend_spec]
    if spec.get("x-bgaExtended") or not extending:
        return spec
    extended = copy.deepcopy(spec)
    for plugin in extending:
        plugin.extend_spec(extended)
    extended["x-bgaExtended"] = True
    return extended


def plan_plugins(plan: dict[str, Any] | None) -> list[Plugin]:
    """The plugins a plan names (`plan["plugins"]`), in its order; no plan: the ones every project has."""
    if plan is None or "plugins" not in plan:
        return ordered([plugin for plugin in REGISTRY.values() if plugin.always])
    return [REGISTRY[entry["name"]] for entry in plan["plugins"] if entry["name"] in REGISTRY]


__all__ = [
    "PLUGINS_DIR",
    "REGISTRY",
    "ActionCheck",
    "AppStartup",
    "CaseContext",
    "Code",
    "Import",
    "Plugin",
    "PluginError",
    "RepositoryFilter",
    "RepositoryMethod",
    "ResponseField",
    "RouterParam",
    "Setting",
    "active_plugins",
    "extended_spec",
    "ordered",
    "plan_plugins",
]
