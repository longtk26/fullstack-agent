"""API contract, contract first (Story 12.3): normalized BackendSpec + plan → OpenAPI 3.1. No LLM.

Every planned operation with its exact operationId, method and path; request and response schemas from the plan's
columns (camelCase API names); the list envelope `{items,total,limit,offset}`; the error envelope per planned
error status; pagination, filter, sort and search query parameters; examples from the spec's `seed[]`, or
synthesized from the field types. The same spec always gives a byte-identical document (`dump_contract`).

`x-bga.fixtures` holds one record set per entity (ids and foreign keys consistent across entities); the frontend
mock layer (Epic 13) serves exactly these records.
"""

import hashlib
import json
import re
import uuid
from typing import Any

from src.modules.shared.domain.backend_spec.naming import to_snake

from .planner import build_plan

CONTRACT_VERSION = "1"
OPENAPI_VERSION = "3.1.0"
EXAMPLE_NAMESPACE = uuid.UUID("6f1c2b8e-7d3a-4f0e-9c55-12b0e5a7c0de")
SYNTHESIZED_RECORDS = 3
ERROR_SCHEMA = "#/components/schemas/ErrorResponse"
_PATH_PARAM = re.compile(r"\{([^}]+)\}")

_BASE_TYPES: dict[str, dict[str, Any]] = {
    "uuid": {"type": "string", "format": "uuid"},
    "string": {"type": "string"},
    "text": {"type": "string"},
    "integer": {"type": "integer"},
    "float": {"type": "number"},
    # Pydantic serializes Decimal as a string and accepts both: the contract allows either.
    "decimal": {"type": ["number", "string"], "format": "decimal"},
    "boolean": {"type": "boolean"},
    "date": {"type": "string", "format": "date"},
    "datetime": {"type": "string", "format": "date-time"},
    "json": {},
}


def field_schema(column: dict[str, Any], nullable: bool | None = None) -> dict[str, Any]:
    """JSON Schema of one plan column (or a column-shaped field). `nullable` overrides the column's own."""
    if column["type"] == "enum":
        values = list(column["enum"]["values"] if "enum" in column else column.get("values") or [])
        schema: dict[str, Any] = {"type": "string", "enum": values}
    else:
        schema = json.loads(json.dumps(_BASE_TYPES[column["type"]]))
    if column["type"] in ("string", "text") and column.get("maxLength"):
        schema["maxLength"] = column["maxLength"]
    if column["type"] in ("integer", "float", "decimal"):
        if column.get("min") is not None:
            schema["minimum"] = column["min"]
        if column.get("max") is not None:
            schema["maximum"] = column["max"]
    is_nullable = column.get("nullable") if nullable is None else nullable
    if is_nullable and "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        schema["type"] = [*types, "null"]
        if "enum" in schema:
            schema["enum"] = [*schema["enum"], None]
    return schema


def _object(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _writable(column: dict[str, Any]) -> bool:
    """Columns a client sends: not generated ids, not `now` timestamps."""
    return not (column.get("default") or {}).get("factory") and not (column.get("default") or {}).get("autoincrement")


def _request_columns(model: dict[str, Any], spec_op: dict[str, Any]) -> list[dict[str, Any]]:
    allowed = (spec_op.get("request") or {}).get("fields")
    return [
        column for column in model["columns"] if _writable(column) and (allowed is None or column["apiName"] in allowed)
    ]


def _properties_columns(properties: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """BackendSpec payload `properties` (FieldDefs) in the shape of plan columns."""
    return [
        {
            **prop,
            "apiName": prop["name"],
            "nullable": prop.get("nullable", not prop.get("required")),
            "default": {"value": prop["default"]} if prop.get("default") is not None else None,
        }
        for prop in properties
    ]


def _required(column: dict[str, Any]) -> bool:
    return not column.get("nullable") and not column.get("default")


# -- examples ----------------------------------------------------------------------------------------------------


def _synthesize(column: dict[str, Any], entity: str, index: int, slug: str) -> Any:
    name, kind = column["apiName"], column["type"]
    if kind == "uuid":
        return str(uuid.uuid5(EXAMPLE_NAMESPACE, f"{slug}:{entity}:{name}:{index}"))
    if kind == "string":
        lower = name.lower()
        if "email" in lower:
            value = f"user{index + 1}@example.com"
        elif lower.endswith("url"):
            value = f"https://example.com/{to_snake(entity)}/{index + 1}.jpg"
        else:
            value = f"{entity} {to_snake(name).replace('_', ' ')} {index + 1}"
        return value[: column["maxLength"]] if column.get("maxLength") else value
    if kind == "text":
        return f"Example {to_snake(name).replace('_', ' ')} of {entity} {index + 1}."
    if kind in ("integer", "float", "decimal"):
        low = column.get("min")
        value: float = (low if low is not None else 1) + index
        if kind != "integer":
            value = round(value + 8.99, 2)
        if column.get("max") is not None:
            value = min(value, column["max"])
        return int(value) if kind == "integer" else value
    if kind == "boolean":
        return index % 2 == 0
    if kind == "date":
        return f"2026-01-{index + 1:02d}"
    if kind == "datetime":
        return f"2026-01-{index + 1:02d}T09:00:00Z"
    if kind == "enum":
        values = column["enum"]["values"]
        return values[index % len(values)] if values else None
    return {}


def build_fixtures(spec: dict[str, Any], plan: dict[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], set[str]]:
    """One record set per entity: the spec's seed rows (completed), else synthesized rows. Returns the records
    by entity and the entities whose records came from the seed."""
    slug = spec["project"].get("slug") or "project"
    models = [model for model in plan["models"] if model.get("entity")]
    by_table = {model["table"]: model for model in models}
    seeds: dict[str, list[dict[str, Any]]] = {}
    for seed in spec.get("seed", []):
        seeds.setdefault(seed["entity"], []).extend(seed["records"])

    records: dict[str, list[dict[str, Any]]] = {}
    for model in models:  # pass 1: own values and primary keys
        entity = model["entity"]
        rows = [dict(row) for row in seeds.get(entity, [])] or [{} for _ in range(SYNTHESIZED_RECORDS)]
        seeded = entity in seeds
        for index, row in enumerate(rows):
            for column in model["columns"]:
                name = column["apiName"]
                if name in row or column.get("foreignKey"):
                    continue
                default = column.get("default") or {}
                if column["primaryKey"]:
                    row[name] = index + 1 if column["type"] == "integer" else _synthesize(column, entity, index, slug)
                elif default.get("factory"):
                    row[name] = _synthesize(column, entity, 0 if seeded else index, slug)
                elif "value" in default and (seeded or column["type"] != "enum"):
                    row[name] = default["value"]
                elif seeded and column["nullable"]:
                    row[name] = None
                else:
                    row[name] = _synthesize(column, entity, index, slug)
        records[entity] = rows
    for model in models:  # pass 2: foreign keys point at the parent's records
        for index, row in enumerate(records[model["entity"]]):
            for column in model["columns"]:
                fk = column.get("foreignKey")
                if not fk or column["apiName"] in row:
                    continue
                table, _, _ = fk["references"].partition(".")
                parent = by_table.get(table)
                parent_rows = records.get(parent["entity"]) if parent else None
                if parent_rows:
                    pk = next(c["apiName"] for c in parent["columns"] if c["primaryKey"])
                    row[column["apiName"]] = parent_rows[index % len(parent_rows)][pk]
                else:
                    row[column["apiName"]] = None
    for model in models:  # column order, so documents diff cleanly
        order = [column["apiName"] for column in model["columns"]]
        records[model["entity"]] = [
            {name: row[name] for name in order if name in row} for row in records[model["entity"]]
        ]
    return records, set(seeds)


def _examples(value: Any, seeded: bool) -> dict[str, Any]:
    return {"seed" if seeded else "synthesized": {"value": value}}


# -- operations --------------------------------------------------------------------------------------------------


def _parameters(op: dict[str, Any], model: dict[str, Any] | None) -> list[dict[str, Any]]:
    by_api = {column["apiName"]: column for column in model["columns"]} if model else {}
    primary = next((c for c in model["columns"] if c["primaryKey"]), None) if model else None
    names = _PATH_PARAM.findall(op["path"])
    parameters = []
    for position, name in enumerate(names):
        column = by_api.get(name)
        if column is None and position == len(names) - 1 and op.get("action") in ("get", "update", "delete"):
            column = primary
        schema = field_schema(column, nullable=False) if column else {"type": "string"}
        parameters.append({"name": name, "in": "path", "required": True, "schema": schema})
    if op.get("action") != "list":
        return parameters
    pagination = op.get("pagination")
    if pagination:
        parameters.append(
            {
                "name": "limit",
                "in": "query",
                "required": False,
                "schema": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": pagination["maxLimit"],
                    "default": pagination["defaultLimit"],
                },
            }
        )
        parameters.append(
            {
                "name": "offset",
                "in": "query",
                "required": False,
                "schema": {"type": "integer", "minimum": 0, "default": 0},
            }
        )
    for flt in op.get("filters", []):
        schema = field_schema(by_api[flt["param"]], nullable=False)
        schema.pop("default", None)
        parameters.append({"name": flt["param"], "in": "query", "required": False, "schema": schema})
    if op.get("sort"):
        values = [value for item in op["sort"] for value in (item["param"], f"-{item['param']}")]
        parameters.append(
            {"name": "sort", "in": "query", "required": False, "schema": {"type": "string", "enum": values}}
        )
    if op.get("search"):
        fields = ", ".join(item["param"] for item in op["search"])
        parameters.append(
            {
                "name": "q",
                "in": "query",
                "required": False,
                "description": f"Case-insensitive match on {fields}",
                "schema": {"type": "string"},
            }
        )
    return parameters


def _mock_plan(
    op: dict[str, Any],
    spec_op: dict[str, Any],
    model: dict[str, Any] | None,
    entity: str,
    models: dict[str, Any],
) -> str:
    """Computes the mock plan for a custom operation (Story 19.5)."""
    method = op.get("method", "GET").upper()
    path = op.get("path", "")
    path_params = _PATH_PARAM.findall(path)
    primary = next((c for c in model["columns"] if c["primaryKey"]), None) if model else None
    pk_names = {"id"}
    if primary:
        pk_names.add(primary["apiName"])
    if entity:
        pk_names.add(f"{entity[0].lower() + entity[1:]}Id")
        pk_names.add(f"{to_snake(entity)}_id")
        pk_names.add(f"{entity.lower()}Id")
    has_id = any(p in pk_names for p in path_params)

    spec_resp = spec_op.get("response") or {}
    has_props = bool(spec_resp.get("properties"))
    resp_entity = spec_resp.get("entity")
    is_entity = bool(not has_props and resp_entity and (resp_entity == entity or resp_entity in models))
    is_array = bool(
        spec_resp.get("cardinality") == "many"
        or spec_resp.get("type") == "array"
        or op.get("pagination")
        or spec_op.get("pagination")
    )

    if method == "GET":
        if has_id and is_entity and not is_array:
            return "record"
        if is_entity:
            return "records"
    elif method in ("POST", "PUT", "PATCH"):
        if has_id and is_entity:
            return "merge"
        if method == "POST" and not has_id and is_entity:
            return "create"
    return "sample"


def _error_responses(op: dict[str, Any]) -> dict[str, Any]:
    by_status: dict[int, list[str]] = {}
    for error in op.get("errors", []):
        codes = by_status.setdefault(error["status"], [])
        if error["code"] not in codes:
            codes.append(error["code"])
    return {
        str(status): {
            "description": " | ".join(codes),
            "content": {"application/json": {"schema": {"$ref": ERROR_SCHEMA}}},
        }
        for status, codes in sorted(by_status.items())
    }


class _Builder:
    def __init__(self, spec: dict[str, Any], plan: dict[str, Any]):
        self.spec = spec
        self.plan = plan
        self.schemas: dict[str, Any] = {
            "ErrorResponse": _object(
                {
                    "error": _object(
                        {"code": {"type": "string"}, "message": {"type": "string"}, "details": {}},
                        ["code", "message"],
                    )
                },
                ["error"],
            )
        }
        self.models = {model["entity"]: model for model in plan["models"] if model.get("entity")}
        self.spec_ops = {op["operationId"]: op for op in spec.get("operations", [])}
        self.fixtures, self.seeded = build_fixtures(spec, plan)

    def entity_schema(self, entity: str) -> str:
        name = f"{entity}Response"
        if name not in self.schemas:
            columns = self.models[entity]["columns"]
            self.schemas[name] = _object(
                {column["apiName"]: field_schema(column) for column in columns},
                [column["apiName"] for column in columns],
            )
        return f"#/components/schemas/{name}"

    def request_schema(self, name: str, columns: list[dict[str, Any]], partial: bool) -> str:
        properties = {}
        for column in columns:
            schema = field_schema(column)
            default = (column.get("default") or {}).get("value")
            if default is not None:
                schema["default"] = default
            properties[column["apiName"]] = schema
        required = [] if partial else [column["apiName"] for column in columns if _required(column)]
        self.schemas[name] = _object(properties, required)
        return f"#/components/schemas/{name}"

    def _sample_response(self, spec_op: dict[str, Any], entity: str, status: int) -> Any:
        if status == 204:
            return None
        spec_resp = spec_op.get("response") or {}
        resp_entity = spec_resp.get("entity")
        if resp_entity and self.fixtures.get(resp_entity):
            return self.fixtures[resp_entity][0]
        if spec_resp.get("properties"):
            slug = self.spec["project"].get("slug") or "project"
            columns = _properties_columns(spec_resp["properties"])
            return {c["apiName"]: _synthesize(c, entity or "Result", 0, slug) for c in columns}
        return {"ok": True}

    def operation(self, module: dict[str, Any], op: dict[str, Any]) -> dict[str, Any]:
        entity = module["entity"]
        model = self.models.get(entity)
        spec_op = self.spec_ops.get(op["operationId"], {})
        action = op.get("action")
        records = self.fixtures.get(entity, [])
        seeded = entity in self.seeded
        operation: dict[str, Any] = {
            "operationId": op["operationId"],
            "summary": op.get("summary") or spec_op.get("summary") or f"{action or 'custom'} {entity}",
            "tags": [module["name"]],
            "x-bga": {"entity": entity, "action": action, "module": module["name"]},
        }
        if op.get("auth"):
            if op["auth"].get("auth"):
                operation["x-bga"]["auth"] = op["auth"]["auth"]
            if op["auth"].get("policy"):
                operation["x-bga"]["policy"] = op["auth"]["policy"]
            operation["security"] = [{"bearerAuth": []}]
        mock_plan = None
        if action is None:
            mock_plan = _mock_plan(op, spec_op, model, entity, self.models)
            operation["x-bga"]["mock"] = mock_plan
        if spec_op.get("description"):
            operation["description"] = spec_op["description"]
        parameters = _parameters(op, model)
        if parameters:
            operation["parameters"] = parameters

        request_columns: list[dict[str, Any]] | None = None
        if action in ("create", "update") and model:
            request_columns = _request_columns(model, spec_op)
        elif action is None and (spec_op.get("request") or {}).get("properties"):
            request_columns = _properties_columns(spec_op["request"]["properties"])
        elif action is None and (spec_op.get("request") or {}).get("entity") in self.models:
            request_columns = _request_columns(self.models[spec_op["request"]["entity"]], spec_op)
        if request_columns is not None:
            name = (op.get("requestDto") or f"{op['handler'].title().replace('_', '')}Request").removesuffix("Dto")
            ref = self.request_schema(name, request_columns, partial=action == "update")
            content: dict[str, Any] = {"schema": {"$ref": ref}}
            if records and action in ("create", "update"):
                names = {column["apiName"] for column in request_columns}
                content["examples"] = _examples({k: v for k, v in records[0].items() if k in names}, seeded)
            operation["requestBody"] = {"required": True, "content": {"application/json": content}}

        status = str(op["status"])
        responses: dict[str, Any] = {}
        if op["status"] == 204:
            responses[status] = {"description": "No content"}
        elif (action == "list" or (action is None and mock_plan == "records" and spec_op.get("pagination"))) and model:
            list_name = op["responseDto"].removesuffix("Dto")
            self.schemas[list_name] = _object(
                {
                    "items": {"type": "array", "items": {"$ref": self.entity_schema(entity)}},
                    "total": {"type": "integer"},
                    "limit": {"type": "integer"},
                    "offset": {"type": "integer"},
                },
                ["items", "total", "limit", "offset"],
            )
            limit = (op.get("pagination") or {}).get("defaultLimit", len(records))
            example = {"items": records[:limit], "total": len(records), "limit": limit, "offset": 0}
            responses[status] = {
                "description": f"Page of {entity} records",
                "content": {
                    "application/json": {
                        "schema": {"$ref": f"#/components/schemas/{list_name}"},
                        "examples": _examples(example, seeded),
                    }
                },
            }
        elif action is None and mock_plan == "records" and not spec_op.get("pagination"):
            response_entity = (spec_op.get("response") or {}).get("entity") or entity
            if response_entity in self.models:
                schema = {"type": "array", "items": {"$ref": self.entity_schema(response_entity)}}
                body: dict[str, Any] = {"schema": schema}
                if self.fixtures.get(response_entity):
                    body["examples"] = _examples(self.fixtures[response_entity], response_entity in self.seeded)
                responses[status] = {
                    "description": f"List of {response_entity} records",
                    "content": {"application/json": body},
                }
            else:
                responses[status] = {
                    "description": "Result",
                    "content": {"application/json": {"schema": {"type": "array"}}},
                }
        else:
            response_entity = (spec_op.get("response") or {}).get("entity") or (entity if action else None)
            if response_entity in self.models:
                body = {"schema": {"$ref": self.entity_schema(response_entity)}}
                if self.fixtures.get(response_entity):
                    body["examples"] = _examples(self.fixtures[response_entity][0], response_entity in self.seeded)
                responses[status] = {"description": f"The {response_entity}", "content": {"application/json": body}}
            elif (spec_op.get("response") or {}).get("properties"):
                columns = _properties_columns(spec_op["response"]["properties"])
                schema = _object({c["apiName"]: field_schema(c) for c in columns}, [c["apiName"] for c in columns])
                responses[status] = {"description": "Result", "content": {"application/json": {"schema": schema}}}
            else:
                responses[status] = {"description": "Result", "content": {"application/json": {"schema": {}}}}
        if action is None and mock_plan == "sample":
            sample = self._sample_response(spec_op, entity, op["status"])
            operation["x-bga"]["sample"] = sample
            if sample is not None and status in responses and "content" in responses[status]:
                responses[status]["content"]["application/json"]["examples"] = _examples(sample, False)
        responses.update(_error_responses(op))
        operation["responses"] = responses
        return operation

    def build(self) -> dict[str, Any]:
        paths: dict[str, dict[str, Any]] = {}
        for module in self.plan["modules"]:
            for op in module["operations"]:
                paths.setdefault(op["path"], {})[op["method"].lower()] = self.operation(module, op)
        project = self.spec["project"]
        canonical = json.dumps(self.spec, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        info: dict[str, Any] = {"title": project["name"], "version": "1.0.0"}
        if project.get("description"):
            info["description"] = project["description"]
        return {
            "openapi": OPENAPI_VERSION,
            "info": info,
            "paths": paths,
            "components": {"schemas": self.schemas},
            "x-bga": {
                "contractVersion": CONTRACT_VERSION,
                "planVersion": self.plan["planVersion"],
                "specSha256": hashlib.sha256(canonical.encode()).hexdigest(),
                "fixtures": self.fixtures,
            },
        }


def build_contract(spec: dict[str, Any], plan: dict[str, Any] | None = None) -> dict[str, Any]:
    """`spec` is the normalized BackendSpec; `plan` defaults to `build_plan(spec)` (also deterministic)."""
    return _Builder(spec, plan or build_plan(spec)).build()


def dump_contract(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def contract_operations(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """operationId → {method, path, operation}."""
    found = {}
    for path, item in contract.get("paths", {}).items():
        for method, operation in item.items():
            if isinstance(operation, dict) and "operationId" in operation:
                found[operation["operationId"]] = {"method": method.upper(), "path": path, "operation": operation}
    return found


def resolve(document: dict[str, Any], schema: Any) -> Any:
    """Follows local `$ref`s (`#/components/...`) until a schema without one."""
    seen = 0
    while isinstance(schema, dict) and "$ref" in schema and seen < 20:
        node: Any = document
        for part in schema["$ref"].removeprefix("#/").split("/"):
            node = node.get(part, {}) if isinstance(node, dict) else {}
        schema, seen = node, seen + 1
    return schema
