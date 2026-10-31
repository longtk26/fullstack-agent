"""Frontend ↔ contract consistency (Story 12.5): a dynamic job is rejected before any engine time is spent when
its FrontendSpec asks for data the backend will never provide.

Every section binding and form names a contract operation; binding params are that operation's parameters with
values of the right type; displayed fields exist in the response; form fields exist in the request with
compatible types and cover what the contract requires. Each issue points at the FrontendSpec (`path`) and, where
it can, at the BackendSpec (`backend_path`), so the UI can mark either editor.
"""

import re
from collections.abc import Iterator
from typing import Any

from src.modules.shared.domain.backend_spec import Severity, SpecIssue
from src.modules.shared.domain.frontend_spec import FrontendIssueCode
from src.orchestrator.contract import build_contract, contract_operations, resolve

C = FrontendIssueCode
_VARIABLE = re.compile(r"^\$(route|query|record)\.[A-Za-z][A-Za-z0-9_]*$")
# FrontendSpec form field type → the JSON type and format it submits
FORM_TYPES: dict[str, tuple[str, str | None]] = {
    "string": ("string", None),
    "text": ("string", None),
    "email": ("string", None),
    "url": ("string", None),
    "tel": ("string", None),
    "password": ("string", None),
    "enum": ("string", None),
    "integer": ("integer", None),
    "number": ("number", None),
    "decimal": ("number", None),
    "boolean": ("boolean", None),
    "date": ("string", "date"),
    "datetime": ("string", "date-time"),
}


def _sections(sections: list[dict[str, Any]], path: str) -> Iterator[tuple[dict[str, Any], str]]:
    """Every section with its JSON path, layout nodes' children included (Story 17.1)."""
    for index, section in enumerate(sections):
        yield section, f"{path}/{index}"
        yield from _sections(section.get("children") or [], f"{path}/{index}/children")


def _types(schema: dict[str, Any]) -> set[str]:
    kind = schema.get("type")
    if kind is None:
        return {"any"}
    return {t for t in (kind if isinstance(kind, list) else [kind]) if t != "null"}


def _value_fits(value: Any, schema: dict[str, Any]) -> str | None:
    """Why a literal value does not fit a parameter schema, or None."""
    if isinstance(value, str) and _VARIABLE.match(value):
        return None
    types = _types(schema)
    if "any" in types:
        return None
    checks = {
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, int | float) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
    }
    if not any(checks.get(kind, False) for kind in types):
        return f"{value!r} is not {' | '.join(sorted(types))}"
    enum = [item for item in schema.get("enum") or [] if item is not None]
    if enum and value not in enum:
        return f"{value!r} is not one of {', '.join(map(str, enum))}"
    if isinstance(value, int | float) and not isinstance(value, bool):
        if schema.get("minimum") is not None and value < schema["minimum"]:
            return f"{value} is below the minimum {schema['minimum']}"
        if schema.get("maximum") is not None and value > schema["maximum"]:
            return f"{value} is above the maximum {schema['maximum']}"
    return None


class _Checker:
    def __init__(self, frontend: dict[str, Any], contract: dict[str, Any], backend: dict[str, Any] | None):
        self.frontend = frontend
        self.contract = contract
        self.operations = contract_operations(contract)
        self.issues: list[SpecIssue] = []
        self.backend = backend or {}
        self.op_index = {op["operationId"]: i for i, op in enumerate(self.backend.get("operations", []))}
        self.entity_index = {entity["name"]: i for i, entity in enumerate(self.backend.get("entities", []))}
        self.field_index = {
            (entity["name"], field["name"]): j
            for entity in self.backend.get("entities", [])
            for j, field in enumerate(entity["fields"])
        }

    def add(self, code: FrontendIssueCode, path: str, message: str, backend_path: str | None = None, hint=None):
        self.issues.append(
            SpecIssue(
                code=code, path=path, message=message, hint=hint, backend_path=backend_path, severity=Severity.ERROR
            )
        )

    def op_pointer(self, operation_id: str) -> str:
        index = self.op_index.get(operation_id)
        return f"/operations/{index}" if index is not None else "/operations"

    def field_pointer(self, operation_id: str, field: str | None = None) -> str | None:
        entity = (self.operations[operation_id]["operation"].get("x-bga") or {}).get("entity")
        if entity not in self.entity_index:
            return self.op_pointer(operation_id)
        if field is not None and (entity, field) in self.field_index:
            return f"/entities/{self.entity_index[entity]}/fields/{self.field_index[(entity, field)]}"
        return f"/entities/{self.entity_index[entity]}/fields"

    def lookup(self, operation_id: str, path: str) -> dict[str, Any] | None:
        found = self.operations.get(operation_id)
        if found is None:
            known = ", ".join(sorted(self.operations)[:20])
            self.add(
                C.CONTRACT_UNKNOWN_OPERATION,
                path,
                f"Operation '{operation_id}' is not in the API contract",
                backend_path="/operations",
                hint=f"Contract operations: {known}",
            )
        return found

    def parameters(self, operation_id: str, given: dict[str, Any], path: str) -> None:
        operation = self.operations[operation_id]["operation"]
        params = {p["name"]: p for p in operation.get("parameters") or []}
        for name, value in given.items():
            parameter = params.get(name)
            if parameter is None:
                self.add(
                    C.CONTRACT_PARAM_MISMATCH,
                    f"{path}/{name}",
                    f"'{operation_id}' has no parameter '{name}'",
                    backend_path=self.op_pointer(operation_id),
                    hint=f"Parameters: {', '.join(params) or '(none)'}",
                )
                continue
            problem = _value_fits(value, resolve(self.contract, parameter.get("schema") or {}))
            if problem:
                self.add(
                    C.CONTRACT_PARAM_MISMATCH,
                    f"{path}/{name}",
                    f"{parameter['in']} parameter '{name}' of '{operation_id}': {problem}",
                    backend_path=self.op_pointer(operation_id),
                )
        for name, parameter in params.items():
            if parameter.get("required") and name not in given:
                self.add(
                    C.CONTRACT_PARAM_MISMATCH,
                    path,
                    f"'{operation_id}' needs the {parameter['in']} parameter '{name}'",
                    backend_path=self.op_pointer(operation_id),
                    hint=f'e.g. "{name}": "$route.{name}"',
                )

    def response_record(self, operation_id: str) -> dict[str, Any]:
        """The record schema a binding displays: the list's item schema, or the response body."""
        operation = self.operations[operation_id]["operation"]
        responses = operation.get("responses") or {}
        success = next((r for s, r in sorted(responses.items()) if s.startswith("2")), {})
        schema = resolve(self.contract, (success.get("content") or {}).get("application/json", {}).get("schema", {}))
        items = (schema.get("properties") or {}).get("items")
        if isinstance(items, dict) and items.get("type") == "array":
            return resolve(self.contract, items.get("items", {}))
        return schema

    def bindings(self) -> None:
        for p_index, page in enumerate(self.frontend.get("pages", [])):
            for section, section_path in _sections(page.get("sections", []), f"/pages/{p_index}/sections"):
                content = section.get("content") or {}
                # 1. Section actions (DataTable, CardGrid, List, DetailView, ActionBar)
                for a_index, action in enumerate(content.get("actions") or []):
                    action_path = f"{section_path}/content/actions/{a_index}"
                    kind = action.get("kind", "link")
                    if kind == "link":
                        target_page = action.get("page")
                        if target_page:
                            known_pages = {p.get("id") for p in self.frontend.get("pages", []) if p.get("id")} | {
                                p.get("route") for p in self.frontend.get("pages", [])
                            }
                            if target_page not in known_pages:
                                self.add(
                                    C.FE_UNKNOWN_PAGE,
                                    f"{action_path}/page",
                                    f"Action '{action.get('id', a_index)}' links to unknown page '{target_page}'",
                                )
                    elif kind == "mutation":
                        op_id = action.get("operationId")
                        if not op_id:
                            self.add(
                                C.CONTRACT_UNKNOWN_OPERATION,
                                f"{action_path}/operationId",
                                "Mutation action requires 'operationId'",
                            )
                            continue
                        found_act = self.lookup(op_id, f"{action_path}/operationId")
                        if found_act is None:
                            continue
                        if found_act["method"] == "GET":
                            self.add(
                                C.CONTRACT_METHOD_MISMATCH,
                                f"{action_path}/operationId",
                                f"Mutation actions call mutating operations; '{op_id}' is GET",
                                backend_path=self.op_pointer(op_id),
                            )
                        if found_act["method"] == "DELETE" and not action.get("confirm"):
                            self.add(
                                C.CONTRACT_PARAM_MISMATCH,
                                f"{action_path}/confirm",
                                f"Delete action '{action.get('id', a_index)}' requires 'confirm'",
                                backend_path=self.op_pointer(op_id),
                            )
                        self.parameters(op_id, action.get("params") or {}, f"{action_path}/params")
                        if action.get("body"):
                            body_content = (
                                (found_act["operation"].get("requestBody") or {})
                                .get("content", {})
                                .get("application/json", {})
                            )
                            body_schema = resolve(self.contract, body_content.get("schema") or {})
                            props = body_schema.get("properties") or {}
                            for k, v in action["body"].items():
                                if k not in props:
                                    self.add(
                                        C.CONTRACT_FIELD_MISSING,
                                        f"{action_path}/body/{k}",
                                        f"The request of '{op_id}' has no field '{k}'",
                                        backend_path=self.op_pointer(op_id),
                                    )
                                else:
                                    prob = _value_fits(v, resolve(self.contract, props[k]))
                                    if prob:
                                        self.add(
                                            C.CONTRACT_FIELD_TYPE_MISMATCH,
                                            f"{action_path}/body/{k}",
                                            f"Action body field '{k}': {prob}",
                                            backend_path=self.op_pointer(op_id),
                                        )

                # 2. Stats items data binding
                if section.get("component") == "Stats":
                    for i_index, item in enumerate(content.get("items") or []):
                        stat_data = item.get("data")
                        if stat_data:
                            stat_op = stat_data.get("operationId")
                            if stat_op:
                                found_stat = self.lookup(
                                    stat_op, f"{section_path}/content/items/{i_index}/data/operationId"
                                )
                                if found_stat:
                                    if found_stat["method"] != "GET":
                                        self.add(
                                            C.CONTRACT_METHOD_MISMATCH,
                                            f"{section_path}/content/items/{i_index}/data/operationId",
                                            f"Stats read data; '{stat_op}' is {found_stat['method']} "
                                            f"{found_stat['path']}",
                                            backend_path=self.op_pointer(stat_op),
                                        )
                                    val = stat_data.get("value", "count")
                                    if val != "count":
                                        stat_record = self.response_record(stat_op)
                                        stat_props = stat_record.get("properties") or {}
                                        if val not in stat_props:
                                            self.add(
                                                C.CONTRACT_FIELD_MISSING,
                                                f"{section_path}/content/items/{i_index}/data/value",
                                                f"The response of '{stat_op}' has no field '{val}'",
                                                backend_path=self.op_pointer(stat_op),
                                            )

                # 3. Section data binding
                data = section.get("data") or {}
                operation_id = data.get("operationId")
                if operation_id is None:
                    continue
                path = f"{section_path}/data"
                found = self.lookup(operation_id, f"{path}/operationId")
                if found is None:
                    continue
                if found["method"] != "GET":
                    self.add(
                        C.CONTRACT_METHOD_MISMATCH,
                        f"{path}/operationId",
                        f"Sections read data; '{operation_id}' is {found['method']} {found['path']} (use a form)",
                        backend_path=self.op_pointer(operation_id),
                    )
                    continue
                self.parameters(operation_id, data.get("params") or {}, f"{path}/params")
                record = self.response_record(operation_id)
                properties = record.get("properties") or {}
                for f_index, field in enumerate(data.get("fields") or []):
                    if field not in properties:
                        self.add(
                            C.CONTRACT_FIELD_MISSING,
                            f"{path}/fields/{f_index}",
                            f"The response of '{operation_id}' has no field '{field}'",
                            backend_path=self.field_pointer(operation_id),
                            hint=f"Fields: {', '.join(properties)}",
                        )

                # 4. List controls (search, filters, sort)
                controls = content.get("controls")
                if controls:
                    op_query_params = {
                        p["name"]: p for p in found["operation"].get("parameters") or [] if p.get("in") == "query"
                    }
                    if controls.get("search") and "q" not in op_query_params and "search" not in op_query_params:
                        self.add(
                            C.CONTRACT_PARAM_MISMATCH,
                            f"{section_path}/content/controls/search",
                            f"'{operation_id}' does not declare a search parameter ('q')",
                            backend_path=self.op_pointer(operation_id),
                        )
                    for f_idx, flt in enumerate(controls.get("filters") or []):
                        if flt not in op_query_params:
                            self.add(
                                C.CONTRACT_PARAM_MISMATCH,
                                f"{section_path}/content/controls/filters/{f_idx}",
                                f"'{operation_id}' has no query parameter '{flt}'",
                                backend_path=self.op_pointer(operation_id),
                            )
                    if controls.get("sort"):
                        sort_param = op_query_params.get("sort")
                        allowed_sort: set[str] = set()
                        if sort_param:
                            sort_schema = resolve(self.contract, sort_param.get("schema") or {})
                            allowed_sort = set(sort_schema.get("enum") or [])
                        for s_idx, s in enumerate(controls.get("sort") or []):
                            bare_s = s.removeprefix("-").removesuffix(":asc").removesuffix(":desc")
                            valid = bool(
                                sort_param
                                and (
                                    not allowed_sort
                                    or s in allowed_sort
                                    or bare_s in allowed_sort
                                    or f"{bare_s}:asc" in allowed_sort
                                    or f"-{bare_s}" in allowed_sort
                                )
                            )
                            if not valid:
                                self.add(
                                    C.CONTRACT_PARAM_MISMATCH,
                                    f"{section_path}/content/controls/sort/{s_idx}",
                                    f"Sort field '{s}' is not allowed by '{operation_id}'",
                                    backend_path=self.op_pointer(operation_id),
                                )

    def forms(self) -> None:
        for f_index, form in enumerate(self.frontend.get("forms", [])):
            path = f"/forms/{f_index}"
            load = form.get("load")
            if load:
                load_op_id = load.get("operationId")
                if load_op_id:
                    found_load = self.lookup(load_op_id, f"{path}/load/operationId")
                    if found_load:
                        if found_load["method"] != "GET":
                            self.add(
                                C.CONTRACT_METHOD_MISMATCH,
                                f"{path}/load/operationId",
                                f"Form load reads data; '{load_op_id}' is {found_load['method']} {found_load['path']}",
                                backend_path=self.op_pointer(load_op_id),
                            )
                        else:
                            self.parameters(load_op_id, load.get("params") or {}, f"{path}/load/params")
                            load_record = self.response_record(load_op_id)
                            load_props = load_record.get("properties") or {}
                            for i, field in enumerate(form.get("fields", [])):
                                fname = field.get("name")
                                if fname and fname not in load_props:
                                    self.add(
                                        C.CONTRACT_FIELD_MISSING,
                                        f"{path}/fields/{i}/name",
                                        f"The response of '{load_op_id}' has no field '{fname}'",
                                        backend_path=self.field_pointer(load_op_id),
                                        hint=f"Fields: {', '.join(load_props)}",
                                    )

            operation_id = form.get("operationId")
            if operation_id is None:
                continue
            found = self.lookup(operation_id, f"{path}/operationId")
            if found is None:
                continue
            if found["method"] == "GET":
                self.add(
                    C.CONTRACT_METHOD_MISMATCH,
                    f"{path}/operationId",
                    f"Forms submit data; '{operation_id}' is GET {found['path']}",
                    backend_path=self.op_pointer(operation_id),
                )
                continue
            self.parameters(operation_id, form.get("params") or {}, f"{path}/params")
            body = (found["operation"].get("requestBody") or {}).get("content", {}).get("application/json", {})
            schema = resolve(self.contract, body.get("schema", {}))
            properties, required = schema.get("properties") or {}, set(schema.get("required") or [])
            collected = set()
            for i, field in enumerate(form.get("fields", [])):
                name, field_path = field["name"], f"{path}/fields/{i}"
                collected.add(name)
                contract_field = properties.get(name)
                if contract_field is None:
                    self.add(
                        C.CONTRACT_FIELD_MISSING,
                        f"{field_path}/name",
                        f"The request of '{operation_id}' has no field '{name}'",
                        backend_path=self.field_pointer(operation_id),
                        hint=f"Fields: {', '.join(properties) or '(no body)'}",
                    )
                    continue
                self.form_field(
                    operation_id, field, resolve(self.contract, contract_field), name in required, field_path
                )
            for name in sorted(required - collected):
                self.add(
                    C.CONTRACT_FIELD_MISSING,
                    f"{path}/fields",
                    f"'{operation_id}' requires '{name}', which the form does not collect",
                    backend_path=self.field_pointer(operation_id, name),
                    hint="Add a field (hidden with a fixed or $route value if the user should not type it)",
                )

    def form_field(self, operation_id: str, field: dict, schema: dict, required: bool, path: str) -> None:
        kind, form_format = FORM_TYPES[field.get("type", "string")]
        types = _types(schema)
        backend_path = self.field_pointer(operation_id, field["name"])
        fits = "any" in types or kind in types or (kind == "integer" and "number" in types)
        if not fits:
            self.add(
                C.CONTRACT_FIELD_TYPE_MISMATCH,
                f"{path}/type",
                f"Form field '{field['name']}' submits {kind}; the contract expects {' | '.join(sorted(types))}",
                backend_path=backend_path,
            )
            return
        contract_format = schema.get("format")
        if contract_format in ("date", "date-time") and form_format != contract_format:
            expected = "date" if contract_format == "date" else "datetime"
            self.add(
                C.CONTRACT_FIELD_TYPE_MISMATCH,
                f"{path}/type",
                f"Form field '{field['name']}' should be type '{expected}' (the contract expects {contract_format})",
                backend_path=backend_path,
            )
        enum = [value for value in schema.get("enum") or [] if value is not None]
        if enum and not field.get("hidden"):
            values = field.get("values") or []
            if field.get("type") != "enum":
                self.add(
                    C.CONTRACT_FIELD_TYPE_MISMATCH,
                    f"{path}/type",
                    f"Form field '{field['name']}' must be an enum of {', '.join(enum)}",
                    backend_path=backend_path,
                )
            elif set(values) - set(enum):
                self.add(
                    C.CONTRACT_FIELD_TYPE_MISMATCH,
                    f"{path}/values",
                    f"Values {', '.join(sorted(set(values) - set(enum)))} are not allowed by the contract",
                    backend_path=backend_path,
                )
        if required and not field.get("required") and field.get("value") is None:
            self.add(
                C.CONTRACT_FIELD_TYPE_MISMATCH,
                f"{path}/required",
                f"'{field['name']}' is required by '{operation_id}'; mark the form field required",
                backend_path=backend_path,
            )

    def seed_assets(self) -> None:
        if not self.backend:
            return
        assets = {a.get("id") for a in self.frontend.get("assets", []) if isinstance(a, dict)}
        seed = self.backend.get("seed") or []
        if isinstance(seed, list):
            for s_index, entry in enumerate(seed):
                if not isinstance(entry, dict):
                    continue
                records = entry.get("records") or []
                if not isinstance(records, list):
                    continue
                for r_index, record in enumerate(records):
                    if not isinstance(record, dict):
                        continue
                    for field_name, value in record.items():
                        if isinstance(value, str) and value.startswith("asset:"):
                            asset_id = value[len("asset:") :]
                            if asset_id not in assets:
                                self.add(
                                    C.FE_UNKNOWN_ASSET,
                                    "/assets",
                                    f"Seed record references unknown asset '{asset_id}'",
                                    backend_path=f"/seed/{s_index}/records/{r_index}/{field_name}",
                                )
        elif isinstance(seed, dict):
            for entity_name, records in seed.items():
                if not isinstance(records, list):
                    continue
                for r_index, record in enumerate(records):
                    if not isinstance(record, dict):
                        continue
                    for field_name, value in record.items():
                        if isinstance(value, str) and value.startswith("asset:"):
                            asset_id = value[len("asset:") :]
                            if asset_id not in assets:
                                self.add(
                                    C.FE_UNKNOWN_ASSET,
                                    "/assets",
                                    f"Seed record references unknown asset '{asset_id}'",
                                    backend_path=f"/seed/{entity_name}/{r_index}/{field_name}",
                                )


def check_consistency(
    frontend: dict[str, Any], contract: dict[str, Any], backend: dict[str, Any] | None = None
) -> list[SpecIssue]:
    """`frontend` and `backend` are the normalized specs; `contract` comes from `build_contract(backend)`."""
    checker = _Checker(frontend, contract, backend)
    checker.bindings()
    checker.forms()
    checker.seed_assets()
    return checker.issues


def check_spec_pair(frontend: dict[str, Any], backend: dict[str, Any]) -> list[SpecIssue]:
    """Both normalized specs: builds the contract the backend lane would get and checks the frontend against it."""
    return check_consistency(frontend, build_contract(backend), backend)
