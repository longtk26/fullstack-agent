"""Schema conformance of a generated backend's OpenAPI to the API contract (Story 12.3).

Stricter than the operation parity check (5.4): for every contract operation the generated app must take the
same parameters (name, location, required, type), accept the same request fields (same required set, compatible
types) and answer with the same status codes and response fields. Extra optional parameters or fields are
allowed; anything a contract client could trip over is a problem, which validation turns into a repair item.

Compatibility is directional. Requests: the app must accept every value the contract allows. Responses: the app
may only return values the contract allows (an integer is a number; `null` only where the contract says so).
"""

from typing import Any

from src.orchestrator.contract import contract_operations, resolve

MAX_DEPTH = 4


def _types(document: dict[str, Any], schema: Any) -> tuple[set[str], dict[str, Any]]:
    """The JSON types a schema admits (`anyOf`/`oneOf` unions and `$ref`s resolved) and its main branch."""
    schema = resolve(document, schema)
    if not isinstance(schema, dict):
        return set(), {}
    for key in ("anyOf", "oneOf"):
        if key in schema:
            types: set[str] = set()
            main: dict[str, Any] = {}
            for branch in schema[key]:
                branch_types, branch_schema = _types(document, branch)
                types |= branch_types
                if branch_types - {"null"} and not main:
                    main = branch_schema
            return types, main
    if "allOf" in schema and len(schema["allOf"]) == 1:
        return _types(document, schema["allOf"][0])
    kind = schema.get("type")
    if kind is None:
        if "enum" in schema:
            return {"string"}, schema
        if "properties" in schema:
            return {"object"}, schema
        return {"any"}, schema
    return set(kind if isinstance(kind, list) else [kind]), schema


def _admits(types: set[str], kind: str) -> bool:
    """An integer is a number."""
    return kind in types or (kind == "integer" and "number" in types)


class _Comparer:
    def __init__(self, contract: dict[str, Any], actual: dict[str, Any]):
        self.contract = contract
        self.actual = actual
        self.problems: list[dict[str, Any]] = []

    def problem(self, operation: str, message: str) -> None:
        self.problems.append({"operation": operation, "message": message})

    def value(self, op: str, where: str, expected: Any, found: Any, direction: str, depth: int = 0) -> None:
        """`direction` is "request" (app must accept the contract's values) or "response" (app must return only
        the contract's values)."""
        want_types, want = _types(self.contract, expected)
        have_types, have = _types(self.actual, found)
        if "any" in want_types or "any" in have_types:
            return
        if direction == "request":
            missing = sorted(t for t in want_types if not _admits(have_types, t))
            if missing:
                self.problem(
                    op, f"{where}: the contract allows {_show(want_types)}, the app accepts {_show(have_types)}"
                )
                return
        else:
            extra = sorted(t for t in have_types if not _admits(want_types, t))
            if extra:
                self.problem(
                    op, f"{where}: the app returns {_show(have_types)}, the contract allows {_show(want_types)}"
                )
                return
        want_format, have_format = want.get("format"), have.get("format")
        if want_format and have_format and want_format != have_format and want_format != "decimal":
            self.problem(op, f"{where}: format {have_format}, the contract says {want_format}")
        want_enum = [v for v in want.get("enum") or [] if v is not None]
        have_enum = [v for v in have.get("enum") or [] if v is not None]
        if want_enum and have_enum:
            outside = set(want_enum) - set(have_enum) if direction == "request" else set(have_enum) - set(want_enum)
            if outside:
                self.problem(op, f"{where}: enum values differ ({', '.join(sorted(map(str, outside)))})")
        if "object" in want_types and depth < MAX_DEPTH:
            self.object(op, where, want, have, direction, depth + 1)
        if "array" in want_types and "items" in want and depth < MAX_DEPTH:
            self.value(op, f"{where}[]", want["items"], have.get("items", {}), direction, depth + 1)

    def object(self, op: str, where: str, want: dict, have: dict, direction: str, depth: int) -> None:
        want_props, have_props = want.get("properties") or {}, have.get("properties") or {}
        if not want_props:
            return
        want_required, have_required = set(want.get("required") or []), set(have.get("required") or [])
        for name, schema in want_props.items():
            path = f"{where}.{name}" if where else name
            if name not in have_props:
                self.problem(op, f"{path}: missing (the contract {'requires' if name in want_required else 'has'} it)")
                continue
            if direction == "request" and (name in want_required) != (name in have_required):
                self.problem(
                    op,
                    f"{path}: {'required' if name in have_required else 'optional'} in the app, "
                    f"{'required' if name in want_required else 'optional'} in the contract",
                )
            if direction == "response" and name in want_required and name not in have_required:
                self.problem(op, f"{path}: the app may omit it, the contract always returns it")
            self.value(op, path, schema, have_props[name], direction, depth)
        if direction == "request":
            for name in sorted(have_required - set(want_props)):
                self.problem(op, f"{where + '.' if where else ''}{name}: required by the app, not in the contract")

    def parameters(self, op: str, want: list[dict], have: list[dict]) -> None:
        have_by = {(p.get("in"), p.get("name")): p for p in have}
        for parameter in want:
            key = (parameter["in"], parameter["name"])
            label = f"{parameter['in']} parameter '{parameter['name']}'"
            found = have_by.pop(key, None)
            if found is None:
                self.problem(op, f"{label}: missing")
                continue
            if bool(found.get("required")) != bool(parameter.get("required")):
                self.problem(
                    op,
                    f"{label}: required={bool(found.get('required'))}, the contract says "
                    f"{bool(parameter.get('required'))}",
                )
            self.value(op, label, parameter.get("schema", {}), found.get("schema", {}), "request")
        for (location, name), parameter in sorted(have_by.items()):
            if parameter.get("required"):
                self.problem(op, f"{location} parameter '{name}': required by the app, not in the contract")

    def operation(self, operation_id: str, want: dict[str, Any], have: dict[str, Any]) -> None:
        op = f"{want['method']} {want['path']}"
        contract_op, actual_op = want["operation"], have["operation"]
        self.parameters(op, contract_op.get("parameters") or [], actual_op.get("parameters") or [])
        want_body = (contract_op.get("requestBody") or {}).get("content", {}).get("application/json")
        have_body = (actual_op.get("requestBody") or {}).get("content", {}).get("application/json")
        if want_body and not have_body:
            self.problem(op, "request body: missing")
        elif want_body:
            self.value(op, "body", want_body.get("schema", {}), have_body.get("schema", {}), "request")
        have_responses = actual_op.get("responses") or {}
        for status, response in (contract_op.get("responses") or {}).items():
            if status not in have_responses:
                self.problem(op, f"response {status}: not declared by the app")
                continue
            if not status.startswith("2"):
                continue  # error bodies follow the shared envelope; the app documents them by description only
            want_schema = (response.get("content") or {}).get("application/json", {}).get("schema")
            have_content = (have_responses[status].get("content") or {}).get("application/json")
            if want_schema and not have_content:
                self.problem(op, f"response {status}: no JSON body")
            elif want_schema:
                self.value(op, f"response {status}", want_schema, have_content.get("schema", {}), "response")
        success = [s for s in have_responses if s.startswith("2")]
        expected = [s for s in contract_op.get("responses") or {} if s.startswith("2")]
        for status in success:
            if status not in expected:
                self.problem(op, f"response {status}: the contract expects {', '.join(expected)}")


def _show(types: set[str]) -> str:
    return " | ".join(sorted(types)) or "nothing"


def compare_contract(contract: dict[str, Any], document: dict[str, Any]) -> list[dict[str, Any]]:
    """Problems as `{operation, message}` (the shape of the other parity checks). Missing operations are left to
    `compare_openapi`, which already reports them."""
    comparer = _Comparer(contract, document)
    actual = contract_operations(document)
    for operation_id, want in sorted(contract_operations(contract).items()):
        have = actual.get(operation_id)
        if have is None or (have["method"], have["path"]) != (want["method"], want["path"]):
            continue
        comparer.operation(operation_id, want, have)
    return comparer.problems
