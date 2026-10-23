"""Minimal placeholder plan so the workflow can run end to end. Story 5.1 replaces it with the full planner."""

from typing import Any

from src.modules.shared.domain.backend_spec.naming import table_name


def skeleton_plan(spec: dict[str, Any]) -> dict[str, Any]:
    modules = []
    for entity in spec.get("entities", []):
        operations = [op for op in spec.get("operations", []) if op.get("entity") == entity["name"]]
        modules.append(
            {
                "name": entity.get("table") or table_name(entity["name"]),
                "entity": entity["name"],
                "operations": [
                    {
                        "operationId": op["operationId"],
                        "method": op["method"],
                        "path": op["path"],
                        "action": op.get("action"),
                    }
                    for op in operations
                ],
                "tests": [
                    {
                        "id": f"{op['operationId'].replace('.', '_')}__ok",
                        "operationId": op["operationId"],
                        "description": "happy path",
                    }
                    for op in operations
                ],
            }
        )
    return {"planVersion": "skeleton", "modules": modules}
