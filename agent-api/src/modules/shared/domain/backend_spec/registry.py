from typing import Any

from .schema_v1 import BackendSpecV1

SPEC_MODELS: dict[str, type[BackendSpecV1]] = {"1.0": BackendSpecV1}
LATEST_SPEC_VERSION = "1.0"


def supported_versions() -> list[str]:
    return list(SPEC_MODELS)


def spec_json_schema(version: str = LATEST_SPEC_VERSION) -> dict[str, Any]:
    schema = SPEC_MODELS[version].model_json_schema(by_alias=True)
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://backend-generation-agent.local/schemas/backend-spec-{version}.json",
        **schema,
    }
