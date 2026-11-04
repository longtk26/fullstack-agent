"""Pair fixes for dynamic drafts: the FrontendSpec and the BackendSpec must agree before a generation starts, and
the user never fixes the pair by hand.

While drafting, the BackendSpec is still a plan, so code first makes the backend follow what the pages need
(`adapt_backend`, before every check): a custom operation gets the request a form posts or the response a section
reads, a list gets the filter, sort or search a page asks for, a create or update form's field joins its entity.
What the backend cannot provide, once the engine's repair rounds are spent, is cut from the frontend
(`prune_frontend`): the action, binding, parameter or field the pair check still rejects. Every change is a note.
"""

import copy
import logging
import re
from collections.abc import Callable
from typing import Any

from src.modules.shared.domain.backend_spec import Severity, SpecIssue, validate_spec_data
from src.modules.shared.domain.backend_spec.naming import to_camel
from src.modules.shared.domain.frontend_spec import validate_frontend_spec_data

from ..checks.consistency import check_spec_pair

logger = logging.getLogger(__name__)

MAX_ROUNDS = 60

# Form field type → BackendSpec field type (`enum` only with values).
FORM_FIELD_TYPES = {
    "string": "string",
    "text": "text",
    "email": "string",
    "url": "string",
    "tel": "string",
    "password": "string",
    "enum": "enum",
    "integer": "integer",
    "number": "float",
    "decimal": "decimal",
    "boolean": "boolean",
    "date": "date",
    "datetime": "datetime",
}
_FIGURE = re.compile(r"(total|sum|amount|value|price|cost|spend|avg|average|balance)", re.I)
_COUNT = re.compile(r"(count|number|qty|quantity)$", re.I)
_MOMENT = re.compile(r"(At|Date|date)$")


def _note(spec: str, path: str, message: str) -> dict[str, Any]:
    return {"spec": spec, "path": path, "message": message, "suggestion": None}


def pair_errors(frontend: Any, backend: Any) -> list[SpecIssue] | None:
    """The pair check's errors, or None while either spec is invalid on its own (the engine repairs those)."""
    fe, be = validate_frontend_spec_data(frontend), validate_spec_data(backend)
    if not fe.report.valid or not be.report.valid or fe.normalized is None or be.normalized is None:
        return None
    try:
        issues = check_spec_pair(fe.normalized, be.normalized)
    except Exception:  # a contract the builder cannot make: leave the pair to the check and the engine
        logger.warning("pair check failed", exc_info=True)
        return None
    return [i for i in issues if i.severity == Severity.ERROR]


# -- pointers ------------------------------------------------------------------------------------------------------


def _tokens(pointer: str) -> list[str]:
    return [t.replace("~1", "/").replace("~0", "~") for t in pointer.split("/")[1:]]


def _get(doc: Any, pointer: str) -> Any:
    node = doc
    for token in _tokens(pointer):
        if isinstance(node, list) and token.isdigit() and int(token) < len(node):
            node = node[int(token)]
        elif isinstance(node, dict) and token in node:
            node = node[token]
        else:
            return None
    return node


def _operation_at(frontend: dict[str, Any], pointer: str) -> tuple[str | None, str]:
    """The operation the frontend element at `pointer` calls: the nearest enclosing object with an `operationId`
    (a form, a section's data, an action, a Stats item's data; a section's controls use its data), and that
    object's pointer."""
    tokens = _tokens(pointer)
    for end in range(len(tokens), 0, -1):
        prefix = "/" + "/".join(tokens[:end])
        node = _get(frontend, prefix)
        if isinstance(node, dict) and isinstance(node.get("operationId"), str):
            return node["operationId"], prefix
        data = node.get("data") if isinstance(node, dict) and node.get("component") else None
        if isinstance(data, dict) and isinstance(data.get("operationId"), str):  # a section's controls read its data
            return data["operationId"], f"{prefix}/data"
    return None, ""


def _quoted(message: str) -> list[str]:
    return re.findall(r"'([^']+)'", message)


# -- the backend follows the frontend ------------------------------------------------------------------------------


def _raw_operation(backend: dict[str, Any], operation_id: str) -> dict[str, Any] | None:
    for op in backend.get("operations") or []:
        if isinstance(op, dict) and op.get("operationId") == operation_id:
            return op
    return None


def _entity(backend: dict[str, Any], name: str | None) -> dict[str, Any] | None:
    for entity in backend.get("entities") or []:
        if isinstance(entity, dict) and entity.get("name") == name:
            return entity
    return None


def _entity_field(entity: dict[str, Any] | None, api_name: str) -> dict[str, Any] | None:
    for item in (entity or {}).get("fields") or []:
        if isinstance(item, dict) and (item.get("name") == api_name or to_camel(str(item.get("name"))) == api_name):
            return item
    return None


def _known_field(backend: dict[str, Any], api_name: str, prefer: str | None = None) -> dict[str, Any] | None:
    """A field of that name on the operation's entity, else on any entity (its type is the best guess)."""
    found = _entity_field(_entity(backend, prefer), api_name)
    if found is not None:
        return found
    for entity in backend.get("entities") or []:
        found = _entity_field(entity, api_name)
        if found is not None:
            return found
    return None


def _definition(name: str, type_: str, *, required: bool = False, values: Any = None) -> dict[str, Any]:
    field: dict[str, Any] = {"name": name, "type": type_}
    if type_ == "enum":
        if isinstance(values, list) and values:
            field["values"] = [str(v) for v in values]
        else:
            field["type"] = "string"
    if required:
        field["required"] = True
    return field


def _from_form_field(backend: dict[str, Any], form_field: dict[str, Any], entity: str | None) -> dict[str, Any]:
    name = form_field["name"]
    known = _known_field(backend, name, entity)
    if known is not None:
        return _definition(name, known["type"], required=bool(form_field.get("required")), values=known.get("values"))
    type_ = FORM_FIELD_TYPES.get(str(form_field.get("type") or "string"), "string")
    return _definition(name, type_, required=bool(form_field.get("required")), values=form_field.get("values"))


def _guessed(backend: dict[str, Any], name: str, entity: str | None) -> dict[str, Any]:
    """A response field the page reads: its type from an entity field of that name, else from the name."""
    known = _known_field(backend, name, entity)
    if known is not None:
        return _definition(name, known["type"], values=known.get("values"))
    if _COUNT.search(name):
        return _definition(name, "integer")
    if _FIGURE.search(name):
        return _definition(name, "decimal")
    if _MOMENT.search(name):
        return _definition(name, "datetime")
    return _definition(name, "string")


_CAMEL = re.compile(r"\b[a-z][a-z0-9]*(?:[A-Z][a-z0-9]*)+\b")
_WORD = re.compile(r"\b[a-z][a-z0-9]*\b")


def _described_fields(backend: dict[str, Any], op: dict[str, Any]) -> list[str]:
    """The fields a custom operation's own words name (`summary`, `description`): camelCase names and the
    entities' one-word fields, outside parentheses (formulas), in order of appearance."""
    text = re.sub(r"\([^)]*\)", " ", f"{op.get('summary') or ''}. {op.get('description') or ''}")
    words = {
        to_camel(str(f.get("name")))
        for e in backend.get("entities") or []
        if isinstance(e, dict)
        for f in e.get("fields") or []
        if isinstance(f, dict) and not f.get("primary")
    }
    found: list[str] = []
    last_end = -2
    for match in sorted([*_CAMEL.finditer(text), *_WORD.finditer(text)], key=lambda m: m.start()):
        name = match.group(0)
        if not (_CAMEL.fullmatch(name) or name in words):
            continue
        # "category name" is the category's name, not a second field.
        compound = not _CAMEL.fullmatch(name) and not text[last_end : match.start()].strip()
        last_end = match.end()
        if not compound and name not in found:
            found.append(name)
    return found


def _payload_properties(op: dict[str, Any], key: str) -> list[dict[str, Any]] | None:
    """A custom operation's request / response properties, created when absent; None when it names an entity
    (that payload is the entity's, changed through the entity instead)."""
    payload = op.get(key)
    if payload is None:
        payload = op[key] = {}
    if not isinstance(payload, dict) or payload.get("entity") or payload.get("fields"):
        return None
    properties = payload.setdefault("properties", [])
    return properties if isinstance(properties, list) else None


Change = Callable[[dict[str, Any]], str | None]


def _changes_for(issue: SpecIssue, frontend: dict[str, Any]) -> tuple[str, Change] | None:
    """The backend change that answers `issue` (applied to a copy, kept if the BackendSpec stays valid), with the
    operation it touches; None when the backend cannot answer it."""
    operation_id, owner = _operation_at(frontend, issue.path)
    if operation_id is None:
        return None
    code, message = str(issue.code), issue.message
    names = _quoted(message)

    def op_of(backend: dict[str, Any]) -> dict[str, Any] | None:
        return _raw_operation(backend, operation_id)

    if code == "CONTRACT_FIELD_MISSING" and message.startswith("The request of"):
        form_field = _get(frontend, issue.path.removesuffix("/name"))
        if not isinstance(form_field, dict) or not isinstance(form_field.get("name"), str):
            return None

        def add_request_field(backend: dict[str, Any]) -> str | None:
            op = op_of(backend)
            if op is None:
                return None
            if op.get("type") == "custom":
                properties = _payload_properties(op, "request")
                if properties is None:
                    return None
                properties.append(_from_form_field(backend, form_field, op.get("entity")))
                return f"'{operation_id}' takes '{form_field['name']}', which its form sends"
            if op.get("type") == "crud" and op.get("action") in ("create", "update"):
                entity = _entity(backend, op.get("entity"))
                if entity is None or _entity_field(entity, form_field["name"]) is not None:
                    return None
                entity.setdefault("fields", []).append(
                    {**_from_form_field(backend, form_field, None), "required": False}
                )
                return f"Entity '{entity['name']}' gains '{form_field['name']}', which the '{operation_id}' form sends"
            return None

        return operation_id, add_request_field

    if code == "CONTRACT_FIELD_MISSING" and message.startswith("The response of") and names[1:]:
        name = names[1]

        def add_response_field(backend: dict[str, Any]) -> str | None:
            op = op_of(backend)
            if op is None or op.get("type") != "custom":
                return None
            properties = _payload_properties(op, "response")
            if properties is None:
                return None
            properties.append(_guessed(backend, name, op.get("entity")))
            return f"'{operation_id}' returns '{name}', which the page reads"

        return operation_id, add_response_field

    if code == "CONTRACT_FIELD_MISSING" and "which the form does not collect" in message and names[1:]:
        name = names[1]

        def optional_request_field(backend: dict[str, Any]) -> str | None:
            op = op_of(backend)
            if op is None or op.get("type") != "custom":
                return None
            for item in (op.get("request") or {}).get("properties") or []:
                if isinstance(item, dict) and item.get("name") == name and item.get("required"):
                    item["required"] = False
                    return f"'{name}' is optional in '{operation_id}': its form does not collect it"
            return None

        return operation_id, optional_request_field

    if code == "CONTRACT_SHAPE_MISMATCH":
        section_data = _get(frontend, owner)
        read = [f for f in (section_data or {}).get("fields") or [] if isinstance(f, str)]

        def list_response(backend: dict[str, Any]) -> str | None:
            op = op_of(backend)
            if op is None or op.get("type") != "custom" or op.get("method") != "GET":
                return None
            response = op.get("response")
            if not isinstance(response, dict):
                response = op["response"] = {}
            response["type"] = "array"
            if not response.get("entity") and not response.get("properties"):
                names = read or _described_fields(backend, op)
                response["properties"] = (
                    [_guessed(backend, name, op.get("entity")) for name in names]
                    if names
                    else [_definition("label", "string"), _definition("value", "decimal")]
                )
            return f"'{operation_id}' returns a list, which the page shows"

        return operation_id, list_response

    if code == "CONTRACT_PARAM_MISMATCH" and names:
        if "does not declare a search parameter" in message:
            kind, name = "search", None
        elif message.startswith("Sort field"):
            kind, name = "sort", names[0].removeprefix("-").removesuffix(":asc").removesuffix(":desc")
        elif "has no query parameter" in message or "has no parameter" in message:
            kind, name = "filters", names[-1]
        else:
            return None

        def query_parameter(backend: dict[str, Any]) -> str | None:
            op = op_of(backend)
            if op is None or op.get("method") != "GET":
                return None
            entity = _entity(backend, op.get("entity"))
            if entity is None:
                return None
            if kind == "search":
                text = [
                    str(f["name"])
                    for f in entity.get("fields") or []
                    if isinstance(f, dict) and f.get("type") in ("string", "text") and not f.get("primary")
                ]
                if not text or op.get("search"):
                    return None
                op["search"] = text
                return f"'{operation_id}' searches {', '.join(text)}, as the page's search box needs"
            field = _entity_field(entity, str(name))
            if field is None:
                return None
            listed = op.setdefault(kind, [])
            if not isinstance(listed, list) or field["name"] in listed:
                return None
            listed.append(field["name"])
            what = "filters by" if kind == "filters" else "sorts by"
            return f"'{operation_id}' {what} '{name}', as the page asks"

        return operation_id, query_parameter

    return None


def adapt_backend(frontend: Any, backend: Any) -> tuple[Any, list[dict[str, Any]]]:
    """The BackendSpec changed to give the pages what they read and send; each change is kept only if the
    BackendSpec stays valid. Works on a copy; returns (backend, notes)."""
    if not isinstance(frontend, dict) or not isinstance(backend, dict):
        return backend, []
    current = copy.deepcopy(backend)
    notes: list[dict[str, Any]] = []
    tried: set[tuple[str, str]] = set()
    for _ in range(MAX_ROUNDS):
        errors = pair_errors(frontend, current)
        if not errors:
            break
        changed = False
        for issue in errors:
            key = (str(issue.code), issue.path)
            if key in tried:
                continue
            tried.add(key)
            found = _changes_for(issue, frontend)
            if found is None:
                continue
            operation_id, change = found
            candidate = copy.deepcopy(current)
            message = change(candidate)
            if message is None or not validate_spec_data(candidate).report.valid:
                continue
            if pair_errors(frontend, candidate) is None:  # valid, but no contract builds from it
                continue
            current = candidate
            index = next(
                (i for i, op in enumerate(current.get("operations") or []) if op.get("operationId") == operation_id),
                None,
            )
            notes.append(_note("backend", f"/operations/{index}" if index is not None else "/operations", message))
            changed = True
            break  # the pair is checked again: one change often answers several errors
        if not changed:
            break
    return current, notes


# -- the last resort: cut what still fails from the frontend ------------------------------------------------------

_ACTION = re.compile(r"^(.*/actions/\d+)(/.*)?$")
_PARAM = re.compile(r"^(.*/data)/params/([^/]+)$")
_FIELD = re.compile(r"^(.*/data)/fields/(\d+)$")
_STAT = re.compile(r"^(.*/items/\d+)/data(/.*)?$")
_BINDING = re.compile(r"^(.*/sections/\d+)/data(/.*)?$")
_CONTROL = re.compile(r"^(.*/content/controls)/(search|filters|sort)(?:/(\d+))?$")
_FORM_FIELD = re.compile(r"^(/forms/\d+)/fields/(\d+)(/.*)?$")
_FORM_LOAD = re.compile(r"^(/forms/\d+)/load(/.*)?$")
_FORM = re.compile(r"^(/forms/\d+)(/.*)?$")


def _cut(pointer: str) -> tuple[str, str, str | None]:
    """What to remove for an error at `pointer`: (kind, the container's pointer, the key or index)."""
    for pattern, kind in ((_ACTION, "action"), (_FORM_LOAD, "load")):
        match = pattern.match(pointer)
        if match:
            return kind, match.group(1), None
    match = _PARAM.match(pointer)
    if match:
        return "param", match.group(1), match.group(2)
    match = _FIELD.match(pointer)
    if match:
        return "field", match.group(1), match.group(2)
    match = _STAT.match(pointer)
    if match:
        return "stat", match.group(1), None
    match = _CONTROL.match(pointer)
    if match:
        return "control", match.group(1), f"{match.group(2)}/{match.group(3) or ''}"
    match = _BINDING.match(pointer)
    if match:
        return "binding", match.group(1), None
    match = _FORM_FIELD.match(pointer)
    if match:
        return "form-field", match.group(1), match.group(2)
    match = _FORM.match(pointer)
    if match:
        return "form", match.group(1), None
    return "none", pointer, None


def _sort_key(pointer: str, key: str | None = None) -> list[tuple[int, Any]]:
    tokens = _tokens(pointer) + ([key.partition("/")[2] or key] if key else [])
    return [(0, int(t)) if t.isdigit() else (1, t) for t in tokens]


def _remove(frontend: dict[str, Any], kind: str, at: str, key: str | None) -> str | None:
    parent_pointer, _, last = at.rpartition("/")
    target = _get(frontend, at)
    if kind == "action":
        actions = _get(frontend, parent_pointer)
        if isinstance(actions, list) and last.isdigit() and int(last) < len(actions):
            removed = actions.pop(int(last))
            return f"Action '{(removed or {}).get('label') or (removed or {}).get('id')}' removed"
    elif kind == "param" and isinstance(target, dict) and isinstance(target.get("params"), dict):
        target["params"].pop(str(key), None)
        return f"Parameter '{key}' removed"
    elif kind == "field" and isinstance(target, dict) and isinstance(target.get("fields"), list):
        index = int(str(key))
        if index < len(target["fields"]):
            name = target["fields"].pop(index)
            if not target["fields"]:
                del target["fields"]
            return f"Field '{name}' removed"
    elif kind in ("stat", "binding") and isinstance(target, dict) and "data" in target:
        del target["data"]
        return "Data binding removed; the section shows its own content"
    elif kind == "control" and isinstance(target, dict):
        name, _, index = str(key).partition("/")
        if name == "search":
            target["search"] = False
            return "Search box removed"
        items = target.get(name)
        if isinstance(items, list) and index.isdigit() and int(index) < len(items):
            return f"{name.capitalize()} '{items.pop(int(index))}' removed"
    elif kind == "load" and isinstance(target, dict) and "load" in target:
        del target["load"]
        return "The form no longer loads the record first"
    elif kind == "form-field" and isinstance(target, dict) and isinstance(target.get("fields"), list):
        index = int(str(key))
        if index < len(target["fields"]):
            removed = target["fields"].pop(index)
            return f"Form field '{(removed or {}).get('name')}' removed"
    elif kind == "form" and isinstance(target, dict) and target.get("operationId"):
        operation_id = target["operationId"]
        target["operationId"] = None
        target.pop("params", None)
        return f"The form no longer submits to '{operation_id}'; it stays on the page"
    return None


def prune_frontend(frontend: Any, backend: Any) -> tuple[Any, list[dict[str, Any]]]:
    """The last resort after the repair rounds: whatever the pair check still rejects is removed from the
    FrontendSpec (the smallest element that holds the error), so the generation can start. Works on a copy;
    returns (frontend, notes); a pair that still fails after three passes is left as it is."""
    if not isinstance(frontend, dict) or not isinstance(backend, dict):
        return frontend, []
    current = copy.deepcopy(frontend)
    notes: list[dict[str, Any]] = []
    for _ in range(3):
        errors = pair_errors(current, backend)
        if not errors:
            break
        cuts: dict[tuple[str, str, str | None], SpecIssue] = {}
        for issue in errors:
            cuts.setdefault(_cut(issue.path), issue)
        # Deepest and last first, so removing one element never shifts the index of another still to remove; an
        # element inside one that is removed anyway is skipped.
        ordered = sorted(cuts, key=lambda c: _sort_key(c[1], c[2]), reverse=True)
        removed_any = False
        for kind, at, key in ordered:
            if kind == "none" or any(other[1] != at and at.startswith(other[1] + "/") for other in cuts):
                continue
            issue = cuts[(kind, at, key)]
            message = _remove(current, kind, at, key)
            if message is None:
                continue
            removed_any = True
            notes.append(_note("frontend", issue.path, f"{message}: {issue.message}"))
        if not removed_any:
            break
    return current, notes
