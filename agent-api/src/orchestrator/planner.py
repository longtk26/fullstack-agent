"""Deterministic architecture planner (Story 5.1): normalized BackendSpec → fastapi-skills implementation plan.

No LLM. The same spec always yields a byte-identical plan (see `dump_plan`). Generation prompts, the conventions
check, the schema check, the OpenAPI parity check and the test coverage check all read this plan.

Naming: Python attributes and database columns are snake_case; the HTTP API (JSON bodies and query parameters)
keeps the spec's camelCase names through Pydantic aliases.
"""

import json
from typing import Any

from src.modules.shared.domain.backend_spec.naming import pluralize, to_pascal, to_snake

PLAN_VERSION = "1"
ENTITIES_PKG = "src/modules/shared/domain/entities"
MODELS_PKG = "src/modules/shared/infrastructure/models"
WRITE_ACTIONS = {"create", "update", "delete"}
CRUD_STATUS = {"create": 201, "get": 200, "list": 200, "update": 200, "delete": 204}

# spec field type → (python type, column type as SQLAlchemy/SQLModel spells it)
TYPE_MAP: dict[str, tuple[str, str]] = {
    "uuid": ("uuid.UUID", "Uuid"),
    "string": ("str", "VARCHAR"),
    "text": ("str", "Text"),
    "integer": ("int", "Integer"),
    "float": ("float", "Float"),
    "decimal": ("decimal.Decimal", "Numeric(18, 4)"),
    "boolean": ("bool", "Boolean"),
    "date": ("datetime.date", "Date"),
    "datetime": ("datetime.datetime", "DateTime(timezone=True)"),
    "enum": ("<enum>", "Enum"),
    "json": ("Any", "JSONB"),
}


def handler_name(operation_id: str, list_action: bool = False) -> str:
    """`task.create` → `create_task`; `task.list` → `list_tasks`; `admin.task.archive` → `archive_admin_task`."""
    *resource, action = operation_id.split(".")
    subject = "_".join(to_snake(part) for part in resource)
    if list_action:
        head, _, last = subject.rpartition("_")
        subject = f"{head}_{pluralize(last)}" if head else pluralize(last)
    return f"{to_snake(action)}_{subject}"


def _usecase_class(handler: str) -> str:
    return f"{to_pascal(handler)}Usecase"


def _enum_class(entity: str, field: str) -> str:
    return f"{entity}{to_pascal(field)}"


def _column(entity: dict[str, Any], field: dict[str, Any]) -> dict[str, Any]:
    python_type, column_type = TYPE_MAP[field["type"]]
    attr = to_snake(field["name"])
    column: dict[str, Any] = {
        "field": field["name"],
        "attr": attr,
        "apiName": field["name"],
        "type": field["type"],
        "pythonType": python_type,
        "columnType": column_type,
        "nullable": bool(field.get("nullable")),
        "primaryKey": bool(field.get("primary")),
        "unique": bool(field.get("unique")),
        "index": bool(field.get("index")),
    }
    if field["type"] == "enum":
        enum_class = _enum_class(entity["name"], field["name"])
        column["pythonType"] = enum_class
        column["enum"] = {
            "class": enum_class,
            "dbName": f"{to_snake(entity['name'])}_{attr}",
            "values": list(field.get("values") or []),
            "module": f"{ENTITIES_PKG}/{to_snake(entity['name'])}_entity.py",
        }
    if field.get("maxLength") is not None:
        column["maxLength"] = field["maxLength"]
        column["columnType"] = f"VARCHAR({field['maxLength']})" if field["type"] == "string" else column_type
    for bound in ("min", "max"):
        if field.get(bound) is not None:
            value = field[bound]
            column[bound] = int(value) if float(value).is_integer() else value
    default = field.get("default")
    if column["primaryKey"] and field["type"] == "uuid":
        column["default"] = {"factory": "uuid.uuid4"}
    elif column["primaryKey"] and field["type"] == "integer":
        column["default"] = {"autoincrement": True}
    elif default == "now" and field["type"] in ("date", "datetime"):
        column["default"] = {"factory": "now (UTC)"}
    elif default is not None:
        column["default"] = {"value": default}
    return column


def _relationships(spec: dict[str, Any]) -> tuple[dict[str, list], list[dict], list[dict]]:
    """Returns (FK columns to add per entity, relationship attributes per model, link models)."""
    by_name = {entity["name"]: entity for entity in spec.get("entities", [])}
    fks: dict[str, list[dict[str, Any]]] = {}
    attributes: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    for rel in spec.get("relationships", []):
        parent, child = by_name[rel["from"]], by_name[rel["to"]]
        parent_pk = next(f for f in parent["fields"] if f.get("primary"))
        parent_attr = to_snake(rel["from"])
        child_collection = pluralize(to_snake(rel["to"]))
        if rel["type"] in ("one-to-many", "one-to-one"):
            fk_field = rel["foreignKey"]
            fks.setdefault(rel["to"], []).append(
                {
                    "field": fk_field,
                    "attr": to_snake(fk_field),
                    "references": f"{parent['table']}.{to_snake(parent_pk['name'])}",
                    "referencesType": parent_pk["type"],
                    "onDelete": rel.get("onDelete") or "RESTRICT",
                    "unique": rel["type"] == "one-to-one",
                }
            )
            many = rel["type"] == "one-to-many"
            attributes.append(
                {
                    "relationship": rel["name"],
                    "type": rel["type"],
                    "parent": {
                        "model": f"{rel['from']}Model",
                        "attr": child_collection if many else to_snake(rel["to"]),
                        "annotation": f'list["{rel["to"]}Model"]' if many else f'Optional["{rel["to"]}Model"]',
                        "backPopulates": parent_attr,
                    },
                    "child": {
                        "model": f"{rel['to']}Model",
                        "attr": parent_attr,
                        "annotation": f'"{rel["from"]}Model"',
                        "backPopulates": child_collection if many else to_snake(rel["to"]),
                    },
                }
            )
        else:
            child_pk = next(f for f in child["fields"] if f.get("primary"))
            link_entity = rel.get("through") or f"{rel['from']}{rel['to']}Link"
            left, right = f"{to_snake(rel['from'])}_id", f"{to_snake(rel['to'])}_id"
            links.append(
                {
                    "relationship": rel["name"],
                    "class": f"{link_entity}Model" if not link_entity.endswith("Model") else link_entity,
                    "table": f"{parent['table']}_{child['table']}",
                    "file": f"{MODELS_PKG}/{to_snake(link_entity)}_model.py",
                    "columns": [
                        {
                            "attr": left,
                            "references": f"{parent['table']}.{to_snake(parent_pk['name'])}",
                            "referencesType": parent_pk["type"],
                            "onDelete": "CASCADE",
                            "primaryKey": True,
                        },
                        {
                            "attr": right,
                            "references": f"{child['table']}.{to_snake(child_pk['name'])}",
                            "referencesType": child_pk["type"],
                            "onDelete": "CASCADE",
                            "primaryKey": True,
                        },
                    ],
                }
            )
            attributes.append(
                {
                    "relationship": rel["name"],
                    "type": "many-to-many",
                    "link": links[-1]["class"],
                    "parent": {
                        "model": f"{rel['from']}Model",
                        "attr": child_collection,
                        "annotation": f'list["{rel["to"]}Model"]',
                        "backPopulates": pluralize(parent_attr),
                    },
                    "child": {
                        "model": f"{rel['to']}Model",
                        "attr": pluralize(parent_attr),
                        "annotation": f'list["{rel["from"]}Model"]',
                        "backPopulates": child_collection,
                    },
                }
            )
    return fks, attributes, links


def _models(spec: dict[str, Any]) -> list[dict[str, Any]]:
    fks, attributes, links = _relationships(spec)
    models = []
    for entity in spec.get("entities", []):
        columns = [_column(entity, field) for field in entity["fields"]]
        by_attr = {column["attr"]: column for column in columns}
        foreign_keys = []
        for fk in fks.get(entity["name"], []):
            column = by_attr.get(fk["attr"])
            if column is None:  # the spec relies on the implicit foreign key: add the column
                python_type, column_type = TYPE_MAP[fk["referencesType"]]
                column = {
                    "field": fk["field"],
                    "attr": fk["attr"],
                    "apiName": fk["field"],
                    "type": fk["referencesType"],
                    "pythonType": python_type,
                    "columnType": column_type,
                    "nullable": fk["onDelete"] == "SET NULL",
                    "primaryKey": False,
                    "unique": False,
                    "index": True,
                    "implicit": True,
                }
                columns.append(column)
                by_attr[fk["attr"]] = column
            if fk["unique"]:
                column["unique"] = True
            column["foreignKey"] = {"references": fk["references"], "onDelete": fk["onDelete"]}
            foreign_keys.append({"column": fk["attr"], "references": fk["references"], "onDelete": fk["onDelete"]})
        name = to_snake(entity["name"])
        models.append(
            {
                "entity": entity["name"],
                "table": entity["table"],
                "class": f"{entity['name']}Model",
                "file": f"{MODELS_PKG}/{name}_model.py",
                "entityClass": f"{entity['name']}Entity",
                "entityFile": f"{ENTITIES_PKG}/{name}_entity.py",
                "primaryKey": next(c["attr"] for c in columns if c["primaryKey"]),
                "columns": columns,
                "foreignKeys": foreign_keys,
                "indexes": [
                    {
                        "name": index.get("name")
                        or f"ix_{entity['table']}_{'_'.join(to_snake(f) for f in index['fields'])}",
                        "columns": [to_snake(f) for f in index["fields"]],
                        "unique": bool(index.get("unique")),
                    }
                    for index in entity.get("indexes", [])
                ],
                "uniqueConstraints": [[to_snake(f) for f in group] for group in entity.get("uniqueConstraints", [])],
                "enums": [c["enum"] for c in columns if "enum" in c],
                "relationships": [
                    {**side, "relationship": attr["relationship"], "type": attr["type"], "link": attr.get("link")}
                    for attr in attributes
                    for side in (attr["parent"], attr["child"])
                    if side["model"] == f"{entity['name']}Model"
                ],
            }
        )
    for link in links:
        models.append(
            {
                "entity": None,
                "table": link["table"],
                "class": link["class"],
                "file": link["file"],
                "linkFor": link["relationship"],
                "primaryKey": [c["attr"] for c in link["columns"]],
                "columns": [
                    {
                        "attr": c["attr"],
                        "type": c["referencesType"],
                        "pythonType": TYPE_MAP[c["referencesType"]][0],
                        "columnType": TYPE_MAP[c["referencesType"]][1],
                        "nullable": False,
                        "primaryKey": True,
                        "unique": False,
                        "index": False,
                        "foreignKey": {"references": c["references"], "onDelete": c["onDelete"]},
                    }
                    for c in link["columns"]
                ],
                "foreignKeys": [
                    {"column": c["attr"], "references": c["references"], "onDelete": c["onDelete"]}
                    for c in link["columns"]
                ],
                "indexes": [],
                "uniqueConstraints": [],
                "enums": [],
                "relationships": [],
            }
        )
    return models


def _operation(op: dict[str, Any], model: dict[str, Any] | None) -> dict[str, Any]:
    action = op.get("action") if op["type"] == "crud" else None
    handler = handler_name(op["operationId"], list_action=action == "list")
    usecase = _usecase_class(handler)
    planned: dict[str, Any] = {
        "operationId": op["operationId"],
        "type": op["type"],
        "action": action,
        "method": op["method"],
        "path": op["path"],
        "handler": handler,
        "usecase": usecase,
        "usecaseDep": f"{usecase}Dep",
        "usecaseFile": f"{handler}_usecase.py",
        "transactional": action in WRITE_ACTIONS or (action is None and op["method"] != "GET"),
        "status": CRUD_STATUS.get(action or "", 200),
        "errors": [],
    }
    if op.get("summary"):
        planned["summary"] = op["summary"]
    entity = model["entity"] if model else None
    if action in ("get", "update", "delete") or (action is None and "{" in op["path"]):
        planned["errors"].append({"status": 404, "exception": "NotFoundException", "code": "NOT_FOUND"})
    if action in ("create", "update"):
        planned["requestDto"] = f"{to_pascal(handler)}RequestDto"
        planned["dtoFile"] = f"{handler}_dto.py"
        planned["errors"].append({"status": 422, "exception": None, "code": "VALIDATION_ERROR"})
        if model and any(c["unique"] and not c["primaryKey"] for c in model["columns"]):
            planned["errors"].append({"status": 409, "exception": "ConflictException", "code": "CONFLICT"})
        if model and model["foreignKeys"]:
            planned["errors"].append({"status": 400, "exception": "BadRequestException", "code": "REFERENCE_NOT_FOUND"})
    if action in ("create", "get", "update"):
        planned["responseDto"] = f"{entity}ResponseDto"
    if action == "list":
        pagination = op.get("pagination") or None
        planned["responseDto"] = f"{to_pascal(handler)}ResponseDto"
        planned["dtoFile"] = f"{handler}_dto.py"
        planned["pagination"] = pagination
        by_api = {c["apiName"]: c for c in model["columns"]} if model else {}
        planned["filters"] = [
            {"param": name, "attr": by_api[name]["attr"], "type": by_api[name]["type"]}
            for name in op.get("filters", [])
            if name in by_api
        ]
        planned["sort"] = [
            {"param": name, "attr": by_api[name]["attr"]} for name in op.get("sort", []) if name in by_api
        ]
        planned["search"] = [
            {"param": name, "attr": by_api[name]["attr"]} for name in op.get("search", []) if name in by_api
        ]
        if planned["sort"]:
            planned["errors"].append({"status": 422, "exception": None, "code": "VALIDATION_ERROR"})
    if op.get("rules"):
        planned["rules"] = list(op["rules"])
    if op.get("auth") == "jwt" or op.get("policy"):
        planned["auth"] = {"auth": op.get("auth"), "policy": op.get("policy")}
    return planned


def _repository_methods(operations: list[dict[str, Any]]) -> list[str]:
    needed = {"create": ["create"], "get": ["find_by_id"], "list": ["list"], "update": ["find_by_id", "update"]}
    needed["delete"] = ["find_by_id", "delete"]
    methods: list[str] = []
    for op in operations:
        for method in needed.get(op["action"] or "", []):
            if method not in methods:
                methods.append(method)
    return methods


def _tests(module: dict[str, Any], model: dict[str, Any]) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []

    def add(op: dict[str, Any], case: str, expect: int, description: str) -> None:
        tests.append(
            {
                "id": f"test_{op['handler']}__{case}",
                "operationId": op["operationId"],
                "case": case,
                "expectStatus": expect,
                "description": description,
            }
        )

    for op in module["operations"]:
        action = op["action"]
        if action == "create":
            add(op, "ok", 201, "valid payload creates the record and returns it")
            add(op, "invalid", 422, "missing required field or wrong type is rejected")
            if any(e["code"] == "CONFLICT" for e in op["errors"]):
                add(op, "conflict", 409, "duplicate value in a unique field is rejected")
            if any(e["code"] == "REFERENCE_NOT_FOUND" for e in op["errors"]):
                add(op, "bad_reference", 400, "a foreign key pointing at a missing record is rejected")
        elif action == "get":
            add(op, "ok", 200, "returns the record")
            add(op, "not_found", 404, "unknown id returns 404 with the error envelope")
        elif action == "list":
            add(op, "ok", 200, "returns {items, total, limit, offset}")
            if op.get("pagination"):
                add(op, "pagination", 200, "limit and offset page through the records; total counts all")
            for flt in op.get("filters", []):
                add(op, f"filter_{to_snake(flt['param'])}", 200, f"?{flt['param']}= returns only matching records")
            if op.get("sort"):
                add(op, "sort", 200, "?sort=<field> ascending and ?sort=-<field> descending")
                add(op, "invalid_sort", 422, "sorting by an undeclared field is rejected")
            if op.get("search"):
                add(op, "search", 200, "?q= matches the declared search fields")
        elif action == "update":
            add(op, "ok", 200, "partial update changes only the sent fields")
            add(op, "not_found", 404, "unknown id returns 404")
            add(op, "invalid", 422, "wrong type is rejected")
        elif action == "delete":
            add(op, "ok", 204, "deletes the record; a later get returns 404")
            add(op, "not_found", 404, "unknown id returns 404")
        else:
            add(op, "ok", op["status"], "custom operation happy path")
    for test in tests:
        test["module"] = module["name"]
        test["file"] = module["testFile"]
    return tests


def build_plan(spec: dict[str, Any]) -> dict[str, Any]:
    """`spec` is the normalized BackendSpec (validate_spec_text(...).normalized)."""
    models = _models(spec)
    by_entity = {m["entity"]: m for m in models if m["entity"]}
    modules, unresolved = [], []
    for entity in spec.get("entities", []):
        model = by_entity[entity["name"]]
        name = entity["table"]
        ops = [_operation(op, model) for op in spec.get("operations", []) if op.get("entity") == entity["name"]]
        if not ops:
            continue
        base = f"src/modules/{name}"
        entity_snake = to_snake(entity["name"])
        dto_files = sorted({op["dtoFile"] for op in ops if "dtoFile" in op} | {f"{entity_snake}_response_dto.py"})
        module = {
            "name": name,
            "entity": entity["name"],
            "model": model["class"],
            "entityClass": model["entityClass"],
            "port": {
                "interface": f"I{entity['name']}Repository",
                "dep": f"I{entity['name']}RepoDep",
                "file": f"{base}/ports/output/{entity_snake}_repository.py",
                "implementation": f"{entity['name']}Repository",
                "implementationFile": f"{base}/infrastructure/persistence/{entity_snake}_repository.py",
                "methods": _repository_methods(ops),
            },
            "usecases": [
                {
                    "class": op["usecase"],
                    "dep": op["usecaseDep"],
                    "file": f"{base}/usecases/{op['usecaseFile']}",
                    "operationId": op["operationId"],
                    "transactional": op["transactional"],
                    "raises": sorted({e["exception"] for e in op["errors"] if e["exception"]}),
                }
                for op in ops
            ],
            "dtoFiles": [f"{base}/presenter/dtos/{file}" for file in dto_files],
            "router": {
                "variable": f"{entity_snake}_router",
                "file": f"{base}/presenter/router.py",
                "prefix": "",
                "tag": name,
            },
            "operations": ops,
            "testFile": f"tests/modules/{name}/test_{entity_snake}_api.py",
        }
        module["tests"] = _tests(module, model)
        modules.append(module)
    for op in spec.get("operations", []):
        if op["type"] == "custom":
            unresolved.append(
                {
                    "kind": "custom_operation",
                    "ref": op["operationId"],
                    "message": "Custom operation: the engine implements it from the description or raises 501",
                }
            )
        if op.get("auth") == "jwt" or op.get("policy"):
            unresolved.append(
                {"kind": "auth", "ref": op["operationId"], "message": "Auth and policies arrive with Epic 10"}
            )
    for key in ("rules", "integrations", "backgroundJobs", "policies"):
        for item in spec.get(key, []):
            unresolved.append(
                {"kind": key, "ref": item.get("id") or item.get("name"), "message": f"`{key}` are not generated yet"}
            )
    if spec.get("auth"):
        unresolved.append({"kind": "auth", "ref": "auth", "message": "JWT auth arrives with Epic 10"})

    return {
        "planVersion": PLAN_VERSION,
        "project": {"name": spec["project"]["name"], "slug": spec["project"].get("slug")},
        "architecture": "fastapi-skills-hexagonal",
        "conventions": {
            "pythonNames": "snake_case attributes and columns",
            "apiNames": "camelCase JSON and query parameters (Pydantic alias_generator=to_camel, populate_by_name)",
            "listResponse": {"items": "list", "total": "int", "limit": "int", "offset": "int"},
            "sortParam": "sort=<field> or sort=-<field>; undeclared field → 422",
            "searchParam": "q",
            "errorBody": {"error": {"code": "str", "message": "str", "details": "any"}},
        },
        "models": models,
        "modules": modules,
        "routers": {
            "file": "src/routers.py",
            "variable": "all_router",
            "order": ["health_router", *(m["router"]["variable"] for m in modules)],
        },
        "dependencies": [],
        "tests": [test for module in modules for test in module["tests"]],
        "unresolved": unresolved,
    }


def dump_plan(plan: dict[str, Any]) -> str:
    return json.dumps(plan, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def planned_operations(plan: dict[str, Any]) -> set[tuple[str, str, str]]:
    return {(op["method"], op["path"], op["operationId"]) for m in plan["modules"] for op in m["operations"]}
