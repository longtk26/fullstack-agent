"""The fallback for integrations no plugin covers (Story 10.1, step 4; was the old story 10.4): an output port and a
stub adapter that raises `NotImplementedError`, its env vars, and an `unresolved` entry, so the generation completes
and a developer (or the engine) knows exactly what to fill in."""

from typing import Any

from src.modules.shared.domain.backend_spec.naming import to_pascal, to_snake

from .base import Plugin, Setting

MODULE = "src/modules/integrations"


def _integrations(spec_or_plan: dict[str, Any]) -> list[dict[str, Any]]:
    """The spec's integrations (in a plan: the ones the planner kept, `plan["integrations"]`)."""
    return list(spec_or_plan.get("integrations") or [])


class IntegrationStubsPlugin(Plugin):
    def __init__(self) -> None:
        super().__init__(name="integration-stubs")

    def applies(self, spec: dict[str, Any]) -> bool:
        return bool(_integrations(spec))

    def plan(self, plan: dict[str, Any], spec: dict[str, Any]) -> None:
        plan["integrations"] = []
        for index, integration in enumerate(_integrations(spec)):
            name = to_snake(integration["name"])
            plan["integrations"].append(
                {"name": name, "class": to_pascal(name), "description": integration.get("description")}
            )
            plan["unresolved"] = [
                entry
                for entry in plan["unresolved"]
                if not (entry["kind"] == "integrations" and entry["ref"] == integration["name"])
            ]
            plan["unresolved"].append(
                {
                    "kind": "integration",
                    "ref": integration["name"],
                    "specPath": f"/integrations/{index}",
                    "message": f"No plugin for '{integration['name']}': implement the stub adapter "
                    f"{MODULE}/infrastructure/adapters/{name}_adapter.py (its port is "
                    f"{MODULE}/ports/output/{name}_port.py)",
                }
            )

    def settings(self, plan: dict[str, Any] | None) -> list[Setting]:
        out = []
        for integration in (plan or {}).get("integrations", []):
            upper = integration["name"].upper()
            out.append(Setting(f"{integration['name']}_base_url", "str", '""', example=f"{upper}_BASE_URL="))
            out.append(Setting(f"{integration['name']}_api_key", "str", '""', example=f"{upper}_API_KEY="))
        return out

    def files(self, plan: dict[str, Any] | None) -> dict[str, str]:
        integrations = (plan or {}).get("integrations", [])
        if not integrations:
            return {}
        files = {
            f"{MODULE}/__init__.py": "",
            f"{MODULE}/ports/__init__.py": "",
            f"{MODULE}/infrastructure/__init__.py": "",
            f"{MODULE}/infrastructure/adapters/__init__.py": "".join(
                f"from .{i['name']}_adapter import I{i['class']}PortDep\n" for i in integrations
            )
            + "\n__all__ = ["
            + ", ".join(f'"I{i["class"]}PortDep"' for i in integrations)
            + "]\n",
        }
        exports = []
        for integration in integrations:
            name, cls = integration["name"], integration["class"]
            about = integration.get("description") or f"The {name} integration."
            files[f"{MODULE}/ports/output/{name}_port.py"] = (
                "from abc import ABC, abstractmethod\nfrom typing import Any\n\n\n"
                f"class I{cls}Port(ABC):\n"
                f'    """{about}"""\n\n'
                "    @abstractmethod\n"
                "    def call(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:\n"
                '        """Performs `action` with `payload` and returns the provider\'s answer."""\n'
            )
            files[f"{MODULE}/infrastructure/adapters/{name}_adapter.py"] = (
                "from typing import Annotated, Any\n\nfrom fastapi import Depends\n\n"
                "from src.configs import config\n"
                f"from src.modules.integrations.ports.output.{name}_port import I{cls}Port\n\n\n"
                f"class {cls}Adapter(I{cls}Port):\n"
                f'    """Stub (Story 10.1): no plugin covers \'{name}\'. Implement `call` against the provider, using\n'
                f"    `config.{name}_base_url` and `config.{name}_api_key` ({name.upper()}_BASE_URL, "
                f'{name.upper()}_API_KEY)."""\n\n'
                "    def __init__(self) -> None:\n"
                f"        self.base_url = config.{name}_base_url\n"
                f"        self.api_key = config.{name}_api_key\n\n"
                "    def call(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:\n"
                f'        raise NotImplementedError("{name}: not implemented yet (stub adapter)")\n\n\n'
                f"I{cls}PortDep = Annotated[I{cls}Port, Depends({cls}Adapter)]\n"
            )
            exports.append((name, cls))
        files[f"{MODULE}/ports/output/__init__.py"] = (
            "".join(f"from .{name}_port import I{cls}Port\n" for name, cls in exports)
            + "from src.modules.integrations.infrastructure.adapters import "
            + ", ".join(f"I{cls}PortDep" for _, cls in exports)
            + "\n\n__all__ = ["
            + ", ".join(f'"I{cls}Port", "I{cls}PortDep"' for _, cls in exports)
            + "]\n"
        )
        return files

    def engine_note(self, plan: dict[str, Any]) -> str | None:
        integrations = plan.get("integrations", [])
        if not integrations:
            return None
        names = ", ".join(
            f"`I{i['class']}PortDep` (`from src.modules.integrations.ports.output import I{i['class']}PortDep`)"
            for i in integrations
        )
        return (
            f"Integrations without a plugin have a port and a stub adapter: {names}. Inject the port where an "
            "operation needs the provider; leave the stub as it is (it raises NotImplementedError)."
        )
