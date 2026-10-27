"""Frontend ↔ contract consistency (Story 12.5): a dynamic job is rejected before any engine time is spent when
its FrontendSpec asks for data the backend will never provide.

Every section binding and form names a contract operation; binding params are that operation's parameters with
values of the right type; displayed fields exist in the response; form fields exist in the request with
compatible types and cover what the contract requires. Each issue points at the FrontendSpec (`path`) and, where
it can, at the BackendSpec (`backend_path`), so the UI can mark either editor.
"""

import re
from typing import Any

from src.modules.shared.domain.backend_spec import Severity, SpecIssue
from src.modules.shared.domain.frontend_spec import FrontendIssueCode
from src.orchestrator.contract import build_contract, contract_operations, resolve

C = FrontendIssueCode
_VARIABLE = re.compile(r"^\$(route|query)\.[A-Za-z][A-Za-z0-9]*$")
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
        backend = backend or {}
        self.op_index = {op["operationId"]: i for i, op in enumerate(backend.get("operations", []))}
        self.entity_index = {entity["name"]: i for i, entity in enumerate(backend.get("entities", []))}
        self.field_index = {
            (entity["name"], field["name"]): j
            for entity in backend.get("entities", [])
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
            for s_index, section in enumerate(page.get("sections", [])):
                data = section.get("data") or {}
                operation_id = data.get("operationId")
                if operation_id is None:
                    continue
                path = f"/pages/{p_index}/sections/{s_index}/data"
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

    def forms(self) -> None:
        for f_index, form in enumerate(self.frontend.get("forms", [])):
            operation_id = form.get("operationId")
            if operation_id is None:
                continue
            path = f"/forms/{f_index}"
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


def check_consistency(
    frontend: dict[str, Any], contract: dict[str, Any], backend: dict[str, Any] | None = None
) -> list[SpecIssue]:
    """`frontend` and `backend` are the normalized specs; `contract` comes from `build_contract(backend)`."""
    checker = _Checker(frontend, contract, backend)
    checker.bindings()
    checker.forms()
    return checker.issues


def check_spec_pair(frontend: dict[str, Any], backend: dict[str, Any]) -> list[SpecIssue]:
    """Both normalized specs: builds the contract the backend lane would get and checks the frontend against it."""
    return check_consistency(frontend, build_contract(backend), backend)
