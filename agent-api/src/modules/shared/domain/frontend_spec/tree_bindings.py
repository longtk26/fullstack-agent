"""Where a tree's data components get their records (Epic 21).

On a static site a container reads a `content` collection. On a dynamic app it binds to the API contract: the
collection key names the entity (`expenses` → `Expense`), and the contract's operations of that entity give the
list, get, create, update and delete operations; `Metric` and `Chart` bind to the entity's **aggregate** operations
(`expense.sumAmount`, `expense.countByCategory`, …) when the BackendSpec declares them, or fall back to the list
operation and compute in the browser. `derive_operations` is the other direction: the operations a BackendSpec
needs for the trees (CRUD the components use plus the aggregates), which the drafting flow adds to the draft.
"""

from typing import Any

from ..backend_spec.naming import singularize, to_camel, to_pascal
from .trees import DATA_AGGREGATE, DATA_CONTAINERS, DATA_WRITE, walk

Contract = dict[str, Any] | None


def entity_for(collection: str) -> str:
    return to_pascal(singularize(collection))


def op_prefix(collection: str) -> str:
    return to_camel(entity_for(collection))


def aggregate_id(collection: str, fn: str, field: str | None, group_by: str | None) -> str:
    """`expense.sumAmount`, `expense.count`, `expense.sumAmountByCategory`."""
    name = fn + (to_pascal(field) if field and fn != "count" else "")
    if group_by:
        name += "By" + to_pascal(group_by)
    return f"{op_prefix(collection)}.{name}"


def _contract_ops(contract: Contract) -> dict[str, dict[str, Any]]:
    if not contract:
        return {}
    from src.orchestrator.integration.contract import contract_operations

    return contract_operations(contract)


def _entity_ops(ops: dict[str, dict[str, Any]], entity: str) -> dict[str, str]:
    """action → operationId for one entity, from the contract's `x-bga`."""
    found: dict[str, str] = {}
    for operation_id, item in ops.items():
        meta = item["operation"].get("x-bga") or {}
        if meta.get("entity") == entity and meta.get("action") and meta["action"] not in found:
            found[meta["action"]] = operation_id
    return found


def bind_tree(
    tree: dict[str, Any],
    mode: str,
    collections: list[str],
    contract: Contract,
    detail_routes: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Writes a `binding` into every data node that needs one and returns notes for what could not bind.
    `detail_routes` maps a page id to its route (for `detailSlug`)."""
    notes: list[dict[str, Any]] = []
    ops = _contract_ops(contract)
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
        if mode == "dynamic":
            entity = entity_for(collection)
            actions = _entity_ops(ops, entity)
            wanted = _wanted_action(node_type, props)
            operation_id = actions.get(wanted)
            if node_type in DATA_AGGREGATE:
                aggregate = aggregate_id(collection, props.get("fn", "count"), props.get("field"), props.get("groupBy"))
                operation_id = aggregate if aggregate in ops else actions.get("list")
                binding["computed"] = operation_id != aggregate  # the browser aggregates the list
            if operation_id is None:
                notes.append(
                    _note(path, f"No '{wanted}' operation for {entity} in the API contract; {node_type} shows nothing")
                )
            else:
                binding["operationId"] = operation_id
                binding["action"] = wanted
        node["binding"] = binding
        if node_type in DATA_CONTAINERS:
            stack.append((depth, collection))
    return notes


def _wanted_action(node_type: str, props: dict[str, Any]) -> str:
    if node_type in DATA_CONTAINERS:
        return DATA_CONTAINERS[node_type]
    if node_type in DATA_AGGREGATE:
        return "list"
    if node_type == "RecordForm":
        return "update" if props.get("mode") == "edit" else "create"
    return "delete" if props.get("action") == "delete" else "update"


def _bind_record_link(node: dict[str, Any], props: dict[str, Any], collection: str | None, routes: dict[str, str]):
    slug = props.get("detailSlug") or props.get("to")
    if isinstance(slug, str) and slug.startswith("page:") and slug[5:] in routes:
        node["binding"] = {"collection": collection, "route": routes[slug[5:]]}


def _note(path: str, message: str) -> dict[str, Any]:
    return {"spec": "frontend", "path": path, "message": message, "suggestion": None}


# -- the operations a BackendSpec needs for the trees ----------------------------------------------------------------


def derive_operations(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """The BackendSpec operations the trees of a dynamic spec use: CRUD per collection the components need, and one
    aggregate per Metric / Chart. Entities are named from the collection keys; the caller merges these into the
    draft's BackendSpec (`drafting.complete_backend_for_trees`) and skips what it already has."""
    wanted: dict[str, dict[str, Any]] = {}
    from .trees import all_trees

    collections = [c["collection"] for c in spec.get("content") or [] if isinstance(c, dict)]
    default = collections[0] if len(collections) == 1 else None
    for tree in all_trees(spec):
        stack: list[tuple[int, str]] = []
        for node, _, depth in walk(tree):
            while stack and stack[-1][0] >= depth:
                stack.pop()
            node_type = node.get("type")
            props = node.get("props") or {}
            if node_type not in DATA_CONTAINERS and node_type not in DATA_AGGREGATE and node_type not in DATA_WRITE:
                continue
            collection = props.get("collection") or (stack[-1][1] if stack else None) or default
            if not isinstance(collection, str):
                continue
            entity, prefix = entity_for(collection), op_prefix(collection)
            table = collection
            if node_type in DATA_CONTAINERS:
                stack.append((depth, collection))
                action = DATA_CONTAINERS[node_type]
                wanted.setdefault(f"{prefix}.{action}", _crud(prefix, entity, table, action, props))
                if action == "list":
                    wanted.setdefault(f"{prefix}.get", _crud(prefix, entity, table, "get", {}))
            elif node_type in DATA_WRITE:
                action = _wanted_action(node_type, props)
                wanted.setdefault(f"{prefix}.{action}", _crud(prefix, entity, table, action, {}))
            else:
                fn, field, group_by = props.get("fn", "count"), props.get("field"), props.get("groupBy")
                operation_id = aggregate_id(collection, fn, field, group_by)
                aggregate: dict[str, Any] = {"fn": fn}
                if field and fn != "count":
                    aggregate["field"] = field
                if group_by:
                    aggregate["groupBy"] = group_by
                if props.get("period"):
                    aggregate["period"] = props["period"]
                wanted.setdefault(
                    operation_id,
                    {
                        "operationId": operation_id,
                        "type": "aggregate",
                        "entity": entity,
                        "method": "GET",
                        "path": f"/{table}/aggregate/{operation_id.split('.', 1)[1]}",
                        "summary": f"{fn} of {entity}"
                        + (f" {field}" if field else "")
                        + (f" by {group_by}" if group_by else ""),
                        "aggregate": aggregate,
                    },
                )
    return list(wanted.values())


def _crud(prefix: str, entity: str, table: str, action: str, props: dict[str, Any]) -> dict[str, Any]:
    method = {"list": "GET", "get": "GET", "create": "POST", "update": "PATCH", "delete": "DELETE"}[action]
    path = f"/{table}" if action in ("list", "create") else f"/{table}/{{id}}"
    op: dict[str, Any] = {
        "operationId": f"{prefix}.{action}",
        "type": "crud",
        "action": action,
        "entity": entity,
        "method": method,
        "path": path,
    }
    if action == "list":
        op["pagination"] = True
        sort = [props["sortBy"]] if isinstance(props.get("sortBy"), str) else []
        for item in props.get("sortFields") or []:
            name = item.get("field") if isinstance(item, dict) else item
            if isinstance(name, str) and name not in sort:
                sort.append(name)
        if sort:
            op["sort"] = sort
        if isinstance(props.get("searchFields"), list):
            op["search"] = [f for f in props["searchFields"] if isinstance(f, str)]
        if isinstance(props.get("categoryField"), str):
            op["filters"] = [props["categoryField"]]
    return op
