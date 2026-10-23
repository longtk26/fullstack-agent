"""Prints the OpenAPI document of the *started* app (the template registers routers in the lifespan)."""

import json

from fastapi.testclient import TestClient

from src.main import app

with TestClient(app):
    print("BGA_OPENAPI_BEGIN")
    print(json.dumps(app.openapi()))
