"""Generation-time backend plugins (Story 10.1): the registry, which plugins a spec turns on, and their order.

Adding a plugin is a `templates/plugins/<name>/` folder (`plugin.json`, `backend/files/**`, later `frontend/files/**`)
and one `Plugin` subclass registered here; codegen calls the hooks of the plugins the plan names (`plan["plugins"]`).
"""

from typing import Any

from .base import (
    PLUGINS_DIR,
    AppStartup,
    Code,
    Import,
    Plugin,
    RepositoryFilter,
    ResponseField,
    RouterParam,
    Setting,
)
from .integrations import IntegrationStubsPlugin
from .rate_limit import RateLimitPlugin

# Every plugin the generator knows, by name. Tests add their own with `monkeypatch.setitem(REGISTRY, ...)`.
REGISTRY: dict[str, Plugin] = {plugin.name: plugin for plugin in (RateLimitPlugin(), IntegrationStubsPlugin())}


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


def plan_plugins(plan: dict[str, Any] | None) -> list[Plugin]:
    """The plugins a plan names (`plan["plugins"]`), in its order; no plan: the ones every project has."""
    if plan is None or "plugins" not in plan:
        return ordered([plugin for plugin in REGISTRY.values() if plugin.always])
    return [REGISTRY[entry["name"]] for entry in plan["plugins"] if entry["name"] in REGISTRY]


__all__ = [
    "PLUGINS_DIR",
    "REGISTRY",
    "AppStartup",
    "Code",
    "Import",
    "Plugin",
    "PluginError",
    "RepositoryFilter",
    "ResponseField",
    "RouterParam",
    "Setting",
    "active_plugins",
    "ordered",
    "plan_plugins",
]
