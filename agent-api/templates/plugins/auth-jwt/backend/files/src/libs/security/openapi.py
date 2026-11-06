"""Every route behind the bearer scheme documents its 401 (Story 22.7): the API contract lists it on each protected
operation, and FastAPI does not add it from the security dependency."""

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

UNAUTHORIZED = {"description": "UNAUTHORIZED: sign in to continue (error envelope: {error: {code, message, details}})"}


def document_unauthorized(app: FastAPI) -> None:
    def openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(title=app.title, version=app.version, description=app.description, routes=app.routes)
        for item in schema.get("paths", {}).values():
            for operation in item.values():
                if isinstance(operation, dict) and operation.get("security"):
                    operation.setdefault("responses", {}).setdefault("401", UNAUTHORIZED)
        app.openapi_schema = schema
        return schema

    app.openapi = openapi  # type: ignore[method-assign]
