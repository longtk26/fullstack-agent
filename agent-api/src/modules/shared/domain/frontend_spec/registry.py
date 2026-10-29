from typing import Any

from .schema_v1 import FrontendSpecV1
from .section_props import SECTION_PROPS

FRONTEND_SPEC_MODELS: dict[str, type[FrontendSpecV1]] = {"1.0": FrontendSpecV1}
LATEST_FRONTEND_SPEC_VERSION = "1.0"


def supported_frontend_versions() -> list[str]:
    return list(FRONTEND_SPEC_MODELS)


def section_props_schemas() -> dict[str, Any]:
    """`$defs` for every built-in section's content model (and the item models they use), Story 17.1."""
    defs: dict[str, Any] = {}
    for model in {model.__name__: model for model in SECTION_PROPS.values()}.values():
        schema = model.model_json_schema(by_alias=True, ref_template="#/$defs/{model}")
        defs |= schema.pop("$defs", {})
        defs[model.__name__] = schema
    return defs


def frontend_spec_json_schema(version: str = LATEST_FRONTEND_SPEC_VERSION) -> dict[str, Any]:
    schema = FRONTEND_SPEC_MODELS[version].model_json_schema(by_alias=True)
    schema["$defs"] |= section_props_schemas()
    # A section's `content` follows its component's props model, so the editor completes and checks it as typed.
    schema["$defs"]["Section"]["allOf"] = [
        {
            "if": {"properties": {"component": {"const": name}}, "required": ["component"]},
            "then": {"properties": {"content": {"$ref": f"#/$defs/{model.__name__}"}}},
        }
        for name, model in SECTION_PROPS.items()
    ]
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://backend-generation-agent.local/schemas/frontend-spec-{version}.json",
        **schema,
    }
