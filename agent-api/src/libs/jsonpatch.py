"""A small RFC 6902 JSON Patch applier (Story 18.10): spec repairs come back as patches, not whole files.

Supports `add`, `replace`, `remove`, `move`, `copy` and `test` with RFC 6901 pointers (`~0`, `~1`, `-` for the end
of an array). Operations apply in order on a copy; the first one that does not apply raises `PatchError` naming
its index, so the caller can report exactly which patch failed.
"""

import copy
from typing import Any


class PatchError(ValueError):
    def __init__(self, index: int, op: dict[str, Any], reason: str):
        super().__init__(f"patch {index} ({op.get('op')} {op.get('path')}): {reason}")
        self.index = index


def _tokens(pointer: str) -> list[str]:
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise ValueError(f"pointer must start with '/': {pointer!r}")
    return [token.replace("~1", "/").replace("~0", "~") for token in pointer[1:].split("/")]


def _walk(doc: Any, tokens: list[str]) -> Any:
    current = doc
    for token in tokens:
        current = _child(current, token)
    return current


def _child(container: Any, token: str) -> Any:
    if isinstance(container, dict):
        if token not in container:
            raise KeyError(token)
        return container[token]
    if isinstance(container, list):
        index = _index(container, token, insert=False)
        return container[index]
    raise KeyError(token)


def _index(items: list[Any], token: str, insert: bool) -> int:
    if token == "-" and insert:
        return len(items)
    if not token.isdigit():
        raise KeyError(token)
    index = int(token)
    if index > len(items) or (not insert and index == len(items)):
        raise IndexError(token)
    return index


def _get(doc: Any, pointer: str) -> Any:
    return _walk(doc, _tokens(pointer))


def _add(doc: Any, pointer: str, value: Any) -> Any:
    tokens = _tokens(pointer)
    if not tokens:
        return value
    parent = _walk(doc, tokens[:-1])
    last = tokens[-1]
    if isinstance(parent, dict):
        parent[last] = value
    elif isinstance(parent, list):
        parent.insert(_index(parent, last, insert=True), value)
    else:
        raise KeyError(last)
    return doc


def _remove(doc: Any, pointer: str) -> Any:
    tokens = _tokens(pointer)
    if not tokens:
        raise ValueError("cannot remove the document root")
    parent = _walk(doc, tokens[:-1])
    last = tokens[-1]
    if isinstance(parent, dict):
        if last not in parent:
            raise KeyError(last)
        return parent.pop(last)
    if isinstance(parent, list):
        return parent.pop(_index(parent, last, insert=False))
    raise KeyError(last)


def apply_patch(doc: Any, patch: list[dict[str, Any]]) -> Any:
    """Returns a patched copy of `doc`; raises `PatchError` on the first operation that does not apply."""
    result = copy.deepcopy(doc)
    for index, op in enumerate(patch):
        if not isinstance(op, dict) or "op" not in op or "path" not in op:
            raise PatchError(index, op if isinstance(op, dict) else {}, "needs 'op' and 'path'")
        kind, path = op["op"], op["path"]
        try:
            if kind == "add":
                result = _add(result, path, copy.deepcopy(op["value"]))
            elif kind == "replace":
                _get(result, path)  # must exist
                if _tokens(path):
                    _remove(result, path)
                result = _add(result, path, copy.deepcopy(op["value"]))
            elif kind == "remove":
                _remove(result, path)
            elif kind == "move":
                value = _remove(result, op["from"])
                result = _add(result, path, value)
            elif kind == "copy":
                result = _add(result, path, copy.deepcopy(_get(result, op["from"])))
            elif kind == "test":
                if _get(result, path) != op["value"]:
                    raise PatchError(index, op, "value differs")
            else:
                raise PatchError(index, op, f"unknown op {kind!r}")
        except PatchError:
            raise
        except KeyError as exc:
            raise PatchError(index, op, f"no such member {exc.args[0]!r}") from exc
        except IndexError as exc:
            raise PatchError(index, op, f"index {exc.args[0]!r} out of range") from exc
        except (ValueError, TypeError) as exc:
            raise PatchError(index, op, str(exc)) from exc
    return result
