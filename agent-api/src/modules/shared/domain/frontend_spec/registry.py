from typing import Any

from .schema_v1 import FrontendSpecV1

FRONTEND_SPEC_MODELS: dict[str, type[FrontendSpecV1]] = {"1.0": FrontendSpecV1}
LATEST_FRONTEND_SPEC_VERSION = "1.0"


def supported_frontend_versions() -> list[str]:
    return list(FRONTEND_SPEC_MODELS)


def frontend_spec_json_schema(version: str = LATEST_FRONTEND_SPEC_VERSION) -> dict[str, Any]:
    schema = FRONTEND_SPEC_MODELS[version].model_json_schema(by_alias=True)
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://backend-generation-agent.local/schemas/frontend-spec-{version}.json",
        **schema,
    }
