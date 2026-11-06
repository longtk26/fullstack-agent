"""Where a tree's data components get their records (Epic 21): a static site's containers read a `content`
collection. (Dynamic apps have no trees: their screens come from the app flow, Epic 22.)
"""

from typing import Any

from .trees import DATA_AGGREGATE, DATA_CONTAINERS, DATA_WRITE, walk


def bind_tree(
    tree: dict[str, Any], collections: list[str], detail_routes: dict[str, str] | None = None
) -> list[dict[str, Any]]:
    """Writes a `binding` into every data node that needs one and returns notes for what could not bind.
    `detail_routes` maps a page id to its route (for `detailSlug`)."""
    notes: list[dict[str, Any]] = []
    default = collections[0] if len(collections) == 1 else None
    stack: list[tuple[int, str | None]] = []  # (depth, collection) of the enclosing container

    for node, path, depth in walk(tree):
        while stack and stack[-1][0] >= depth:
            stack.pop()
        node_type = node.get("type")
        props = node.get("props") or {}
        if node_type not in DATA_CONTAINERS and node_type not in DATA_AGGREGATE and node_type not in DATA_WRITE:
            if node_type in ("RecordLink", "RecordAction") and (stack or props.get("collection")):
                _bind_record_link(node, props, stack[-1][1] if stack else props.get("collection"), detail_routes or {})
            continue
        collection = props.get("collection") or (stack[-1][1] if stack else None) or default
        if not isinstance(collection, str):
            notes.append(_note(path, f"{node_type} names no collection and the site has several; it shows nothing"))
            continue
        binding: dict[str, Any] = {"collection": collection}
        node["binding"] = binding
        if node_type in DATA_CONTAINERS:
            stack.append((depth, collection))
    return notes


def _bind_record_link(node: dict[str, Any], props: dict[str, Any], collection: str | None, routes: dict[str, str]):
    slug = props.get("detailSlug") or props.get("to")
    if isinstance(slug, str) and slug.startswith("page:") and slug[5:] in routes:
        node["binding"] = {"collection": collection, "route": routes[slug[5:]]}


def _note(path: str, message: str) -> dict[str, Any]:
    return {"spec": "frontend", "path": path, "message": message, "suggestion": None}
