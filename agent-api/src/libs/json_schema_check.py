"""A small JSON Schema check for model answers (Story 24.1, Epic 24 D3: structured output is checked in code too).

Covers the keywords our answer schemas use (`drafting/answer_schema.py` keeps only what Gemini's structured output
documents, and Epic 26's schemas use the same set): type, properties, required, items, enum, anyOf, $ref / $defs,
additionalProperties, minItems, maxItems, minimum, maximum. Other keywords (description, title, format) are ignored.
The point is to catch an answer of the wrong shape before the envelope is applied, with errors short enough to send
back to the model in one repair round; the spec validators still check meaning.
"""

from typing import Any

MAX_ERRORS = 20
_TYPES: dict[str, tuple[type, ...]] = {
    "object": (dict,),
    "array": (list,),
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "null": (type(None),),
}


def _is(value: Any, kind: str) -> bool:
    if kind in ("integer", "number") and isinstance(value, bool):
        return False
    if kind == "integer" and isinstance(value, float):
        return value.is_integer()
    expected = _TYPES.get(kind)
    return expected is None or isinstance(value, expected)


def _resolve(schema: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    seen = 0
    while isinstance(schema, dict) and "$ref" in schema and seen < 20:
        ref = str(schema["$ref"])
        if not ref.startswith("#/"):
            return {}
        target: Any = root
        for part in ref[2:].split("/"):
            target = target.get(part.replace("~1", "/").replace("~0", "~"), {}) if isinstance(target, dict) else {}
        schema, seen = target, seen + 1
    return schema if isinstance(schema, dict) else {}


def schema_errors(value: Any, schema: dict[str, Any] | None) -> list[str]:
    """Problems of `value` against `schema`, as `<json path>: <what>`; empty when it fits."""
    if not schema:
        return []
    errors: list[str] = []
    _check(value, schema, schema, "$", errors)
    return errors[:MAX_ERRORS]


def _check(value: Any, schema: dict[str, Any], root: dict[str, Any], path: str, errors: list[str]) -> None:
    if len(errors) >= MAX_ERRORS:
        return
    schema = _resolve(schema, root)
    if not schema:
        return
    if "anyOf" in schema:
        options = [option for option in schema["anyOf"] if isinstance(option, dict)]
        if options and not any(not schema_errors_at(value, option, root) for option in options):
            errors.append(f"{path}: matches none of the allowed shapes")
            return
    kinds = schema.get("type")
    if kinds is not None:
        kinds = kinds if isinstance(kinds, list) else [kinds]
        if not any(_is(value, kind) for kind in kinds):
            errors.append(f"{path}: expected {' or '.join(kinds)}, got {_name(value)}")
            return
    if "enum" in schema and value not in schema["enum"]:
        allowed = ", ".join(repr(item) for item in schema["enum"][:10])
        errors.append(f"{path}: {value!r} is not one of {allowed}")
    if isinstance(value, dict):
        properties = schema.get("properties") or {}
        for name in schema.get("required") or []:
            if name not in value:
                errors.append(f"{path}: missing required '{name}'")
        extra = schema.get("additionalProperties", True)
        for key, item in value.items():
            if key in properties:
                _check(item, properties[key], root, f"{path}.{key}", errors)
            elif extra is False:
                errors.append(f"{path}: unexpected property '{key}'")
            elif isinstance(extra, dict):
                _check(item, extra, root, f"{path}.{key}", errors)
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: at least {schema['minItems']} item(s), got {len(value)}")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: at most {schema['maxItems']} item(s), got {len(value)}")
        if isinstance(schema.get("items"), dict):
            for index, item in enumerate(value):
                _check(item, schema["items"], root, f"{path}[{index}]", errors)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: {value} is below {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: {value} is above {schema['maximum']}")


def schema_errors_at(value: Any, schema: dict[str, Any], root: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    _check(value, schema, root, "$", errors)
    return errors


def _name(value: Any) -> str:
    for kind in ("null", "boolean", "integer", "number", "string", "array", "object"):
        if _is(value, kind):
            return kind
    return type(value).__name__
