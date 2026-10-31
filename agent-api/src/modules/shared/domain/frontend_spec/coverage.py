"""Operation coverage and the Manage area (Story 19.7).

Pure functions:
- `uncovered_operations(frontend_spec, contract) -> list[str]`: operations no data binding, form, action,
  Stats item or journey step references.
- `add_manage_area(frontend_spec, contract) -> tuple[spec, notes]`: deterministic, idempotent addition of
  `/manage` index and `/manage/<plural>` CRUD pages for entities with uncovered operations.
"""

import copy
import re
from typing import Any

from src.modules.shared.domain.backend_spec.naming import to_snake
from src.orchestrator.contract import contract_operations, resolve


def _label(identifier: str) -> str:
    """Human-readable label for camelCase or snake_case identifiers."""
    words = re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?=[A-Z][a-z]|\b)", identifier)
    return " ".join(word.capitalize() for word in words) if words else identifier.capitalize()


def _slug(text: str) -> str:
    """Valid slug: lowercase alphanumeric separated by hyphens."""
    s = re.sub(r"[^a-zA-Z0-9]+", "-", to_snake(text)).strip("-").lower()
    return re.sub(r"-+", "-", s)


def _ident(text: str) -> str:
    """Valid identifier: alphanumeric and underscores, starts with a letter."""
    s = re.sub(r"[^a-zA-Z0-9_]+", "_", to_snake(text)).strip("_")
    return s if s and s[0].isalpha() else f"op_{s}"


def _iter_sections(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for section in sections:
        result.append(section)
        if section.get("children"):
            result.extend(_iter_sections(section["children"]))
    return result


def covered_operations(frontend_spec: dict[str, Any]) -> set[str]:
    """All API operations referenced anywhere by the frontend spec."""
    covered: set[str] = set()

    # 1. Sections (bindings, actions, stats)
    for page in frontend_spec.get("pages") or []:
        for section in _iter_sections(page.get("sections") or []):
            # Data binding
            data = section.get("data") or {}
            if data.get("operationId"):
                covered.add(data["operationId"])

            # Content actions
            content = section.get("content") or {}
            for action in content.get("actions") or []:
                if action.get("operationId"):
                    covered.add(action["operationId"])

            # Stats items
            if section.get("component") == "Stats":
                for item in content.get("items") or []:
                    stat_data = item.get("data") or {}
                    if stat_data.get("operationId"):
                        covered.add(stat_data["operationId"])

    # 2. Forms (submit and load)
    for form in frontend_spec.get("forms") or []:
        if form.get("operationId"):
            covered.add(form["operationId"])
        if form.get("load") and form["load"].get("operationId"):
            covered.add(form["load"]["operationId"])

    # 3. Journeys (Story 19.8)
    for journey in frontend_spec.get("journeys") or []:
        for step in journey.get("steps") or []:
            if step.get("operationId"):
                covered.add(step["operationId"])

    return covered


def uncovered_operations(frontend_spec: dict[str, Any], contract: dict[str, Any]) -> list[str]:
    """Operations in the contract that no data binding, form, action, Stats item or journey step references."""
    operations = contract_operations(contract)
    covered = covered_operations(frontend_spec)
    return sorted(op_id for op_id in operations if op_id not in covered)


def _needs_signin(op_entry: dict[str, Any]) -> bool:
    raw_op = op_entry["operation"]
    if raw_op.get("security"):
        return True
    xbga = raw_op.get("x-bga") or {}
    if xbga.get("auth") or xbga.get("policy"):
        return True
    return False


def _form_fields_from_schema(contract: dict[str, Any], schema_ref_or_dict: dict[str, Any]) -> list[dict[str, Any]]:
    schema = resolve(contract, schema_ref_or_dict)
    props = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    fields = []
    for name, prop_schema in props.items():
        if name in ("id", "createdAt", "updatedAt"):
            continue
        p = resolve(contract, prop_schema)
        raw_type = p.get("type")
        types = {t for t in (raw_type if isinstance(raw_type, list) else [raw_type]) if t and t != "null"}
        p_format = p.get("format")
        field_type = "string"
        values = None
        if "enum" in p:
            field_type = "enum"
            values = [v for v in p["enum"] if v is not None]
        elif p_format == "date-time":
            field_type = "datetime"
        elif p_format == "date":
            field_type = "date"
        elif "boolean" in types:
            field_type = "boolean"
        elif "integer" in types:
            field_type = "integer"
        elif "number" in types:
            field_type = "number"
        elif "string" in types and p.get("maxLength", 0) > 255:
            field_type = "text"

        field: dict[str, Any] = {
            "name": name,
            "type": field_type,
            "label": _label(name),
            "required": name in required,
        }
        if values:
            field["values"] = values
        if "maxLength" in p:
            field["maxLength"] = p["maxLength"]
        fields.append(field)
    return fields


def remove_manage_area(frontend_spec: dict[str, Any]) -> dict[str, Any]:
    """Pure function: strips the generated Manage area (pages, forms, content, navigation)."""
    spec = copy.deepcopy(frontend_spec)
    spec["pages"] = [
        p
        for p in spec.get("pages") or []
        if not (p.get("id") or "").startswith("manage-") and not (p.get("route") or "").startswith("/manage")
    ]
    spec["forms"] = [
        f
        for f in spec.get("forms") or []
        if not (f.get("id") or "").startswith("manage-") and not (f.get("id") or "").startswith("manage_")
    ]
    if spec.get("layout", {}).get("header", {}).get("navigation"):
        spec["layout"]["header"]["navigation"] = [
            nav
            for nav in spec["layout"]["header"]["navigation"]
            if nav.get("page") not in ("manage-index", "manage")
            and not (nav.get("page") or "").startswith("manage-")
            and not (nav.get("href") or "").startswith("/manage")
        ]
    spec["content"] = [c for c in spec.get("content") or [] if c.get("collection") != "manageEntities"]
    return spec


def add_manage_area(frontend_spec: dict[str, Any], contract: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Deterministic, idempotent Manage area covering uncovered operations. Returns (new_spec, notes)."""
    spec = remove_manage_area(frontend_spec)
    notes: list[str] = []

    # 2. Inspect operations and check sign-in requirements
    ops = contract_operations(contract)
    signin_ops = {op_id for op_id, entry in ops.items() if _needs_signin(entry)}
    for op_id in sorted(signin_ops):
        notes.append(f"'{op_id}' needs sign-in, which generated frontends do not have yet")

    uncovered = uncovered_operations(spec, contract)
    available_uncovered = [op_id for op_id in uncovered if op_id not in signin_ops]

    if not available_uncovered:
        return spec, notes

    # 3. Group by entity
    by_entity: dict[str, list[str]] = {}
    for op_id in available_uncovered:
        entity = (ops[op_id]["operation"].get("x-bga") or {}).get("entity") or "System"
        by_entity.setdefault(entity, []).append(op_id)

    # 4. Generate Manage area for each entity
    schemas = contract.get("components", {}).get("schemas", {})
    entity_cards = []

    for entity in sorted(by_entity):
        entity_snake = to_snake(entity).replace("_", "-")
        plural = f"{entity_snake}s"
        entity_title = _label(entity)
        plural_title = _label(plural)

        entity_ops = {
            op_id: {**entry, "operationId": op_id}
            for op_id, entry in ops.items()
            if (entry["operation"].get("x-bga") or {}).get("entity") == entity and op_id not in signin_ops
        }

        list_op = next(
            (e for e in entity_ops.values() if (e["operation"].get("x-bga") or {}).get("action") == "list"), None
        )
        get_op = next(
            (e for e in entity_ops.values() if (e["operation"].get("x-bga") or {}).get("action") == "get"), None
        )
        create_op = next(
            (e for e in entity_ops.values() if (e["operation"].get("x-bga") or {}).get("action") == "create"), None
        )
        update_op = next(
            (e for e in entity_ops.values() if (e["operation"].get("x-bga") or {}).get("action") == "update"), None
        )
        delete_op = next(
            (e for e in entity_ops.values() if (e["operation"].get("x-bga") or {}).get("action") == "delete"), None
        )

        custom_ops = [
            e
            for e in entity_ops.values()
            if (e["operation"].get("x-bga") or {}).get("action") is None and e["operationId"] in available_uncovered
        ]

        has_list_page = list_op is not None or any(
            not any("id" in p.lower() for p in re.findall(r"\{([^}]+)\}", cop["path"])) for cop in custom_ops
        )

        entity_cards.append(
            {
                "title": plural_title,
                "description": f"Manage {plural_title.lower()}",
                "slug": plural if has_list_page else f"{plural}/new",
            }
        )

        resp_schema = schemas.get(f"{entity}Response") or {}
        props = resp_schema.get("properties") or {}
        fields = [f for f in props if f != "id"] or ["id"]

        # 4a. List Page (/manage/<plural>)
        if has_list_page:
            list_page_id = f"manage-{plural}"
            table_actions: list[dict[str, Any]] = []
            if get_op:
                table_actions.append(
                    {
                        "id": "view",
                        "label": "View",
                        "kind": "link",
                        "page": f"manage-{plural}-detail",
                        "params": {"id": "$record.id"},
                    }
                )
            if update_op and get_op:
                table_actions.append(
                    {
                        "id": "edit",
                        "label": "Edit",
                        "kind": "link",
                        "page": f"manage-{plural}-edit",
                        "params": {"id": "$record.id"},
                    }
                )
            if delete_op:
                table_actions.append(
                    {
                        "id": "delete",
                        "label": "Delete",
                        "kind": "mutation",
                        "operationId": delete_op["operationId"],
                        "params": {"id": "$record.id"},
                        "confirm": f"Delete this {entity_title.lower()}?",
                        "variant": "destructive",
                    }
                )

            list_sections: list[dict[str, Any]] = []
            if create_op:
                list_sections.append(
                    {
                        "id": f"manage-{plural}-bar",
                        "component": "ActionBar",
                        "content": {
                            "actions": [
                                {
                                    "id": "new",
                                    "label": f"New {entity_title}",
                                    "kind": "link",
                                    "page": f"manage-{plural}-new",
                                }
                            ]
                        },
                    }
                )

            if list_op:
                controls_dict: dict[str, Any] = {}
                op_q_params = {
                    p["name"]: p for p in list_op["operation"].get("parameters") or [] if p.get("in") == "query"
                }
                if "q" in op_q_params or "search" in op_q_params:
                    controls_dict["search"] = True
                filters = [p for p in op_q_params if p not in ("q", "search", "sort", "limit", "offset")]
                if filters:
                    controls_dict["filters"] = sorted(filters)
                sort_param = op_q_params.get("sort")
                if sort_param:
                    sort_enum = (sort_param.get("schema") or {}).get("enum") or []
                    if sort_enum:
                        controls_dict["sort"] = [s for s in sort_enum if not s.startswith("-")]

                table_content: dict[str, Any] = {"actions": table_actions}
                if controls_dict:
                    table_content["controls"] = controls_dict

                list_sections.append(
                    {
                        "id": f"manage-{plural}-table",
                        "component": "DataTable",
                        "content": table_content,
                        "data": {
                            "operationId": list_op["operationId"],
                            "params": {},
                            "fields": fields,
                        },
                    }
                )

            # Custom non-id operations on list page
            for cop in custom_ops:
                path_params = re.findall(r"\{([^}]+)\}", cop["path"])
                if not any("id" in p.lower() for p in path_params):
                    req_body = (
                        (cop["operation"].get("requestBody") or {})
                        .get("content", {})
                        .get("application/json", {})
                        .get("schema")
                    )
                    req_props = (resolve(contract, req_body).get("properties") if req_body else {}) or {}
                    cop_slug = _slug(cop["operationId"])
                    cop_ident = _ident(cop["operationId"])
                    if not req_props:
                        list_sections.append(
                            {
                                "id": f"manage-{plural}-{cop_slug}",
                                "component": "ActionBar",
                                "content": {
                                    "actions": [
                                        {
                                            "id": cop_ident,
                                            "label": _label(cop["operationId"].split(".")[-1]),
                                            "kind": "mutation",
                                            "operationId": cop["operationId"],
                                        }
                                    ]
                                },
                            }
                        )
                    else:
                        form_id = f"manage_{cop_ident}"
                        spec.setdefault("forms", []).append(
                            {
                                "id": form_id,
                                "operationId": cop["operationId"],
                                "params": {},
                                "fields": _form_fields_from_schema(contract, req_body),
                                "submitLabel": _label(cop["operationId"].split(".")[-1]),
                                "onSuccess": {"toast": f"{_label(cop['operationId'].split('.')[-1])} executed"},
                            }
                        )
                        list_sections.append(
                            {
                                "id": f"manage-{plural}-{cop_slug}-section",
                                "component": "Form",
                                "form": form_id,
                                "content": {"title": _label(cop["operationId"].split(".")[-1])},
                            }
                        )

            spec.setdefault("pages", []).append(
                {
                    "id": list_page_id,
                    "route": f"/manage/{plural}",
                    "title": plural_title,
                    "sections": list_sections,
                }
            )

        # 4b. Create Page (/manage/<plural>/new)
        if create_op:
            form_id = f"manage_new_{to_snake(entity)}"
            req_body = (create_op["operation"].get("requestBody") or {}).get("content", {}).get(
                "application/json", {}
            ).get("schema") or {}
            form_fields = _form_fields_from_schema(contract, req_body) or [
                {"name": f, "type": "string", "label": _label(f)} for f in fields[:4]
            ]
            create_nav = f"manage-{plural}" if has_list_page else "manage-index"
            spec.setdefault("forms", []).append(
                {
                    "id": form_id,
                    "operationId": create_op["operationId"],
                    "params": {},
                    "fields": form_fields,
                    "submitLabel": f"Create {entity_title}",
                    "onSuccess": {"toast": f"{entity_title} created", "navigate": create_nav},
                }
            )
            spec.setdefault("pages", []).append(
                {
                    "id": f"manage-{plural}-new",
                    "route": f"/manage/{plural}/new",
                    "title": f"New {entity_title}",
                    "sections": [{"id": f"manage-{plural}-new-form", "component": "Form", "form": form_id}],
                }
            )

        # 4c. Detail Page (/manage/<plural>/[id])
        if get_op:
            detail_actions: list[dict[str, Any]] = []
            if update_op:
                detail_actions.append(
                    {
                        "id": "edit",
                        "label": "Edit",
                        "kind": "link",
                        "page": f"manage-{plural}-edit",
                        "params": {"id": "$record.id"},
                    }
                )
            if delete_op:
                detail_actions.append(
                    {
                        "id": "delete",
                        "label": "Delete",
                        "kind": "mutation",
                        "operationId": delete_op["operationId"],
                        "params": {"id": "$record.id"},
                        "confirm": f"Delete this {entity_title.lower()}?",
                        "variant": "destructive",
                        "onSuccess": {"navigate": f"manage-{plural}"},
                    }
                )

            detail_sections: list[dict[str, Any]] = []

            # Custom id operations
            for cop in custom_ops:
                path_params = re.findall(r"\{([^}]+)\}", cop["path"])
                if any("id" in p.lower() for p in path_params):
                    req_body = (
                        (cop["operation"].get("requestBody") or {})
                        .get("content", {})
                        .get("application/json", {})
                        .get("schema")
                    )
                    req_props = (resolve(contract, req_body).get("properties") if req_body else {}) or {}
                    cop_slug = _slug(cop["operationId"])
                    cop_ident = _ident(cop["operationId"])
                    if not req_props:
                        detail_actions.append(
                            {
                                "id": cop_ident,
                                "label": _label(cop["operationId"].split(".")[-1]),
                                "kind": "mutation",
                                "operationId": cop["operationId"],
                                "params": {"id": "$record.id"},
                            }
                        )
                    else:
                        c_form_id = f"manage_detail_{cop_ident}"
                        spec.setdefault("forms", []).append(
                            {
                                "id": c_form_id,
                                "operationId": cop["operationId"],
                                "params": {"id": "$route.id"},
                                "fields": _form_fields_from_schema(contract, req_body),
                                "submitLabel": _label(cop["operationId"].split(".")[-1]),
                                "onSuccess": {"toast": f"{_label(cop['operationId'].split('.')[-1])} executed"},
                            }
                        )
                        detail_sections.append(
                            {
                                "id": f"manage-{plural}-{cop_slug}-detail-form",
                                "component": "Form",
                                "form": c_form_id,
                                "content": {"title": _label(cop["operationId"].split(".")[-1])},
                            }
                        )

            detail_sections.insert(
                0,
                {
                    "id": f"manage-{plural}-detail-view",
                    "component": "DetailView",
                    "content": {"actions": detail_actions},
                    "data": {
                        "operationId": get_op["operationId"],
                        "params": {"id": "$route.id"},
                        "fields": fields,
                    },
                },
            )

            spec.setdefault("pages", []).append(
                {
                    "id": f"manage-{plural}-detail",
                    "route": f"/manage/{plural}/[id]",
                    "title": entity_title,
                    "sections": detail_sections,
                }
            )

        # 4d. Edit Page (/manage/<plural>/[id]/edit)
        if update_op and get_op:
            form_id = f"manage_edit_{to_snake(entity)}"
            req_body = (update_op["operation"].get("requestBody") or {}).get("content", {}).get(
                "application/json", {}
            ).get("schema") or {}
            form_fields = _form_fields_from_schema(contract, req_body) or [
                {"name": f, "type": "string", "label": _label(f)} for f in fields[:4]
            ]
            spec.setdefault("forms", []).append(
                {
                    "id": form_id,
                    "operationId": update_op["operationId"],
                    "params": {"id": "$route.id"},
                    "load": {"operationId": get_op["operationId"], "params": {"id": "$route.id"}},
                    "fields": form_fields,
                    "submitLabel": f"Save {entity_title}",
                    "onSuccess": {"toast": f"{entity_title} updated", "navigate": f"manage-{plural}-detail"},
                }
            )
            spec.setdefault("pages", []).append(
                {
                    "id": f"manage-{plural}-edit",
                    "route": f"/manage/{plural}/[id]/edit",
                    "title": f"Edit {entity_title}",
                    "sections": [{"id": f"manage-{plural}-edit-form", "component": "Form", "form": form_id}],
                }
            )

    # 5. Add /manage index page and navigation
    if entity_cards:
        spec.setdefault("content", []).append(
            {
                "collection": "manageEntities",
                "records": entity_cards,
            }
        )
        spec.setdefault("pages", []).insert(
            0,
            {
                "id": "manage-index",
                "route": "/manage",
                "title": "Manage",
                "sections": [
                    {
                        "id": "manage-entities-grid",
                        "component": "CardGrid",
                        "content": {
                            "title": "Manage",
                            "description": "Administrative records and operations",
                        },
                        "data": {
                            "collection": "manageEntities",
                            "fields": ["title", "description"],
                        },
                    }
                ],
            },
        )

        header_nav = spec.setdefault("layout", {}).setdefault("header", {}).setdefault("navigation", [])
        if not any(nav.get("page") in ("manage-index", "manage") or nav.get("href") == "/manage" for nav in header_nav):
            header_nav.append({"label": "Manage", "page": "manage-index"})

    return spec, notes
