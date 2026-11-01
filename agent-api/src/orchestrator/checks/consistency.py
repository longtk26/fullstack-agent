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

    def add(
        self,
        code: FrontendIssueCode,
        path: str,
        message: str,
        backend_path: str | None = None,
        hint=None,
        warning: bool = False,
    ):
        self.issues.append(
            SpecIssue(
                code=code,
                path=path,
                message=message,
                hint=hint,
                backend_path=backend_path,
                severity=Severity.WARNING if warning else Severity.ERROR,
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
        if schema.get("type") == "array" and "items" in schema:
            return resolve(self.contract, schema["items"])
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

    def coverage(self) -> None:
        from src.modules.shared.domain.frontend_spec import uncovered_operations

        uncovered = uncovered_operations(self.frontend, self.contract)
        for op_id in uncovered:
            found = self.operations.get(op_id)
            reason = "not referenced in the frontend"
            if found:
                op = found["operation"]
                if op.get("security") or (op.get("x-bga") or {}).get("auth") or (op.get("x-bga") or {}).get("policy"):
                    reason = f"'{op_id}' needs sign-in, which generated frontends do not have yet"
            self.add(
                C.FE_OPERATION_UNUSED,
                "/pages",
                f"API operation '{op_id}' is uncovered: {reason}",
                warning=True,
                backend_path=self.op_pointer(op_id) if op_id in self.operations else None,
            )

    def journeys(self) -> None:
        sections_by_id: dict[str, dict[str, Any]] = {}
        forms_by_id = {f.get("id"): f for f in self.frontend.get("forms") or []}
        for p_index, page in enumerate(self.frontend.get("pages") or []):
            for sec, _ in _sections(page.get("sections") or [], f"/pages/{p_index}/sections"):
                if sec.get("id"):
                    sections_by_id[sec["id"]] = sec

        for j_index, journey in enumerate(self.frontend.get("journeys") or []):
            for s_index, step in enumerate(journey.get("steps") or []):
                step_path = f"/journeys/{j_index}/steps/{s_index}"
                op_id = step.get("operationId")
                if op_id and op_id not in self.operations:
                    self.add(
                        C.CONTRACT_UNKNOWN_OPERATION,
                        f"{step_path}/operationId",
                        f"Journey step references unknown operation '{op_id}'",
                    )
                sec_id = step.get("section")
                if sec_id and sec_id in sections_by_id:
                    sec = sections_by_id[sec_id]
                    if step.get("do") == "action" and step.get("action"):
                        for act in (sec.get("content") or {}).get("actions") or []:
                            if act.get("id") == step["action"] and act.get("operationId"):
                                act_op = act["operationId"]
                                if act_op not in self.operations:
                                    self.add(
                                        C.CONTRACT_UNKNOWN_OPERATION,
                                        f"{step_path}/action",
                                        f"Journey action '{step['action']}' references unknown operation '{act_op}'",
                                    )
                    elif step.get("do") == "submit":
                        form_id = sec.get("form")
                        if form_id and form_id in forms_by_id:
                            f = forms_by_id[form_id]
                            f_op = f.get("operationId")
                            if f_op and f_op not in self.operations:
                                self.add(
                                    C.CONTRACT_UNKNOWN_OPERATION,
                                    f"{step_path}/section",
                                    f"Journey form '{form_id}' references unknown operation '{f_op}'",
                                )


def check_consistency(
    frontend: dict[str, Any], contract: dict[str, Any], backend: dict[str, Any] | None = None
) -> list[SpecIssue]:
    """`frontend` and `backend` are the normalized specs; `contract` comes from `build_contract(backend)`."""
    checker = _Checker(frontend, contract, backend)
    checker.bindings()
    checker.forms()
    checker.seed_assets()
    checker.coverage()
    checker.journeys()
    return checker.issues


def check_spec_pair(frontend: dict[str, Any], backend: dict[str, Any]) -> list[SpecIssue]:
    """Both normalized specs: builds the contract the backend lane would get and checks the frontend against it."""
    return check_consistency(frontend, build_contract(backend), backend)


def reconcile_spec_pair(
    frontend: dict[str, Any], backend: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Auto-heals FrontendSpec inconsistencies against the BackendSpec contract:
    - Clears dangling/unknown or invalid operationIds on forms so they become client-only forms
    - Prunes form fields not in request schema, or adds hidden defaults for missing required fields
    - Clears unknown load.operationId on forms
    - Converts mutation actions with unknown operations to link actions
    - Adds confirmation prompt to DELETE actions if missing
    - Clears unknown operationIds from section data bindings or stats items
    - Prunes unsupported section controls (search/filter/sort)
    Returns (healed_frontend, notes).
    """
    if not isinstance(frontend, dict) or not isinstance(backend, dict):
        return frontend, []

    try:
        contract = build_contract(backend)
    except Exception:
        return frontend, []

    ops = contract_operations(contract)
    notes: list[dict[str, Any]] = []

    # 1. Forms
    forms = frontend.get("forms")
    if isinstance(forms, list):
        for f_idx, form in enumerate(forms):
            if not isinstance(form, dict):
                continue
            f_id = form.get("id") or f"form-{f_idx}"
            op_id = form.get("operationId")
            if op_id:
                if op_id not in ops:
                    form["operationId"] = None
                    notes.append(
                        {
                            "spec": "frontend",
                            "path": f"/forms/{f_idx}/operationId",
                            "message": (
                                f"Operation '{op_id}' is not in the API contract; "
                                f"cleared form '{f_id}' to client-only submission."
                            ),
                            "suggestion": None,
                        }
                    )
                elif ops[op_id]["method"] == "GET":
                    form["operationId"] = None
                    notes.append(
                        {
                            "spec": "frontend",
                            "path": f"/forms/{f_idx}/operationId",
                            "message": f"Operation '{op_id}' is GET; cleared form '{f_id}' to client-only submission.",
                            "suggestion": None,
                        }
                    )
                else:
                    found_op = ops[op_id]
                    op_params = found_op["operation"].get("parameters") or []
                    for p in op_params:
                        if p.get("in") == "path" and p.get("required", True):
                            p_name = p.get("name")
                            if p_name:
                                if not isinstance(form.get("params"), dict):
                                    form["params"] = {}
                                if p_name not in form["params"]:
                                    form["params"][p_name] = f"$route.{p_name}"

                    body_content = (
                        (found_op["operation"].get("requestBody") or {}).get("content", {}).get("application/json", {})
                    )
                    schema = resolve(contract, body_content.get("schema") or {})
                    props = schema.get("properties") or {}
                    required = set(schema.get("required") or [])

                    if props and isinstance(form.get("fields"), list):
                        valid_fields = []
                        for fld_idx, fld in enumerate(form["fields"]):
                            if isinstance(fld, dict):
                                fname = fld.get("name")
                                if fname in props:
                                    valid_fields.append(fld)
                                else:
                                    notes.append(
                                        {
                                            "spec": "frontend",
                                            "path": f"/forms/{f_idx}/fields/{fld_idx}",
                                            "message": f"Field '{fname}' not in request for '{op_id}'; removed.",
                                            "suggestion": None,
                                        }
                                    )
                        form["fields"] = valid_fields

                    existing_names = {f.get("name") for f in form.get("fields") or [] if isinstance(f, dict)}
                    for req_name in sorted(required - existing_names):
                        prop_schema = resolve(contract, props.get(req_name) or {})
                        types = _types(prop_schema)
                        field_type = "string"
                        val: Any = ""
                        if "integer" in types or "number" in types:
                            field_type = "integer"
                            val = 0
                        elif "boolean" in types:
                            field_type = "boolean"
                            val = False
                        form.setdefault("fields", []).append(
                            {
                                "name": req_name,
                                "type": field_type,
                                "hidden": True,
                                "value": val,
                            }
                        )
                        notes.append(
                            {
                                "spec": "frontend",
                                "path": f"/forms/{f_idx}/fields",
                                "message": f"Added required hidden field '{req_name}' to form '{f_id}'.",
                                "suggestion": None,
                            }
                        )

            load = form.get("load")
            if isinstance(load, dict):
                load_op = load.get("operationId")
                if load_op and (load_op not in ops or ops[load_op]["method"] != "GET"):
                    del form["load"]
                    notes.append(
                        {
                            "spec": "frontend",
                            "path": f"/forms/{f_idx}/load",
                            "message": f"Invalid load operationId '{load_op}' removed from form '{f_id}'.",
                            "suggestion": None,
                        }
                    )
                elif load_op and load_op in ops:
                    load_params = ops[load_op]["operation"].get("parameters") or []
                    for p in load_params:
                        if p.get("in") == "path" and p.get("required", True):
                            p_name = p.get("name")
                            if p_name:
                                if not isinstance(load.get("params"), dict):
                                    load["params"] = {}
                                if p_name not in load["params"]:
                                    load["params"][p_name] = f"$route.{p_name}"

    # 2. Pages and sections
    pages = frontend.get("pages")
    known_pages: set[str] = set()
    first_page: str = "/"
    if isinstance(pages, list):
        known_pages = {p.get("id") for p in pages if isinstance(p, dict) and p.get("id")} | {
            p.get("route") for p in pages if isinstance(p, dict) and p.get("route")
        }
        for p in pages:
            if isinstance(p, dict) and (p.get("id") or p.get("route")):
                first_page = p.get("id") or p.get("route")
                break
        for p_idx, page in enumerate(pages):
            if not isinstance(page, dict):
                continue
            for sec, sec_path in _sections(page.get("sections") or [], f"/pages/{p_idx}/sections"):
                if not isinstance(sec, dict):
                    continue
                content = sec.get("content")
                if isinstance(content, dict):
                    # Actions
                    actions = content.get("actions")
                    if isinstance(actions, list):
                        for a_idx, action in enumerate(actions):
                            if not isinstance(action, dict):
                                continue
                            if action.get("kind") == "link":
                                target_page = action.get("page")
                                if target_page and target_page not in known_pages:
                                    action["page"] = first_page
                            elif action.get("kind") == "mutation":
                                act_op = action.get("operationId")
                                if not act_op or act_op not in ops or ops[act_op]["method"] == "GET":
                                    action["kind"] = "link"
                                    action["page"] = action.get("page") or first_page
                                    action.pop("operationId", None)
                                    action.pop("body", None)
                                    action.pop("params", None)
                                    notes.append(
                                        {
                                            "spec": "frontend",
                                            "path": f"{sec_path}/content/actions/{a_idx}",
                                            "message": (
                                                f"Mutation action with invalid operation '{act_op}' converted to link."
                                            ),
                                            "suggestion": None,
                                        }
                                    )
                                else:
                                    if ops[act_op]["method"] == "DELETE" and not action.get("confirm"):
                                        action["confirm"] = "Are you sure you want to proceed?"
                                    act_params = ops[act_op]["operation"].get("parameters") or []
                                    for p in act_params:
                                        if p.get("in") == "path" and p.get("required", True):
                                            p_name = p.get("name")
                                            if p_name:
                                                if not isinstance(action.get("params"), dict):
                                                    action["params"] = {}
                                                if p_name not in action["params"]:
                                                    action["params"][p_name] = f"$route.{p_name}"
                    # Stats
                    if sec.get("component") == "Stats" and isinstance(content.get("items"), list):
                        for i_idx, item in enumerate(content["items"]):
                            if isinstance(item, dict) and isinstance(item.get("data"), dict):
                                stat_op = item["data"].get("operationId")
                                if stat_op and (stat_op not in ops or ops[stat_op]["method"] != "GET"):
                                    del item["data"]
                                    notes.append(
                                        {
                                            "spec": "frontend",
                                            "path": f"{sec_path}/content/items/{i_idx}/data",
                                            "message": f"Stats item invalid operation '{stat_op}' removed.",
                                            "suggestion": None,
                                        }
                                    )

                # Section data binding
                data = sec.get("data")
                if isinstance(data, dict):
                    sec_op = data.get("operationId")
                    if sec_op:
                        if sec_op not in ops or ops[sec_op]["method"] != "GET":
                            del sec["data"]
                            notes.append(
                                {
                                    "spec": "frontend",
                                    "path": f"{sec_path}/data",
                                    "message": f"Section data binding with invalid operation '{sec_op}' removed.",
                                    "suggestion": None,
                                }
                            )
                        else:
                            sec_path_params = ops[sec_op]["operation"].get("parameters") or []
                            for p in sec_path_params:
                                if p.get("in") == "path" and p.get("required", True):
                                    p_name = p.get("name")
                                    if p_name:
                                        if not isinstance(data.get("params"), dict):
                                            data["params"] = {}
                                        if p_name not in data["params"]:
                                            data["params"][p_name] = f"$route.{p_name}"

                            if isinstance(content, dict) and isinstance(content.get("controls"), dict):
                                controls = content["controls"]
                                op_params = {
                                    p["name"]: p
                                    for p in ops[sec_op]["operation"].get("parameters") or []
                                    if p.get("in") == "query"
                                }
                                if controls.get("search") and "q" not in op_params and "search" not in op_params:
                                    controls["search"] = False
                                if isinstance(controls.get("filters"), list):
                                    controls["filters"] = [f for f in controls["filters"] if f in op_params]
                                if controls.get("sort") and "sort" not in op_params:
                                    controls["sort"] = []

    return frontend, notes
