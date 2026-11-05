"""Screen planner (Story 22.3): the app outline + the BackendSpec and its contract → the app's FrontendSpec. Pure and
deterministic, no model.

The pages are ordinary FrontendSpec pages whose sections are the app kit's (`APP_SECTIONS`); every binding in them
(operation, parameters, fields, forms) is written here from the contract, never by the model, and passes the pair
check. One section carries one binding, so the pair check and the coverage scan see every one of them: a parent's
detail page lists each child in its own `AppList` (`content.tab`), the dashboard has one `AppDashboard` per figure.

| Contract | Screen |
|---|---|
| `list` | `/<plural>`: `AppList` (search, filters, sort; row actions view, edit, delete) |
| `get` | `/<plural>/[id]`: `AppDetail`, then an `AppList` tab per child entity |
| `create` | `/<plural>/new` (`AppForm`); a child's: `/<parent>/[id]/<plural>/new`, the parent from the route |
| `update` | `/<plural>/[id]/edit` (`AppForm`, loaded from `get`) |
| `delete` | a row and detail action with a confirm dialog |
| custom on a record | a detail action (and a row action when it has no body); a body opens its `AppForm` in a dialog |
| custom list | a tab on the parent when it filters by the parent, else a page of its own in the navigation |
| custom on the collection | a summary (`AppDetail`) or an `AppActions` button on the list page |
| aggregate | a figure or chart on the dashboard (code adds the aggregate operations the outline's dashboard names) |
"""

from dataclasses import dataclass, field
from typing import Any

from src.modules.shared.domain.backend_spec import validate_spec_data
from src.modules.shared.domain.backend_spec.naming import pluralize, to_camel, to_kebab, to_pascal
from src.modules.shared.domain.frontend_spec.coverage import uncovered_operations
from src.orchestrator.integration.contract import contract_operations, resolve

from ...checks.consistency import _response_record
from .outline import humanize

SPEC_VERSION = "1.0"
LIST_CONTROLS = frozenset({"limit", "offset", "sort", "q", "search", "page", "pageSize"})
SKIPPED_SOURCES = frozenset({"currentUser", "server", "upload"})  # the server sets them (uploads: Story 22.7)
RECENT = 5  # records in a dashboard's recent list
RECENT_LISTS = 2  # entities with a recent list on the dashboard


def _note(path: str, message: str) -> dict[str, Any]:
    return {"spec": "frontend", "path": path, "message": message, "suggestion": None}


@dataclass
class AppScreens:
    """What the planner hands back: the FrontendSpec and its notes (decisions; operations it could not place)."""

    spec: dict[str, Any]
    assumptions: list[dict[str, Any]] = field(default_factory=list)
    unresolved: list[dict[str, Any]] = field(default_factory=list)


# -- aggregates -------------------------------------------------------------------------------------------------------


def _date_field(entity: dict[str, Any]) -> str | None:
    """The date a period counts from: a `…At` timestamp set on creation, else the first date or datetime."""
    fields = [f for f in entity.get("fields") or [] if f.get("type") in ("date", "datetime")]
    created = next((f["name"] for f in fields if f.get("default") == "now"), None)
    return created or next((f["name"] for f in fields), None)


def _aggregate(item: dict[str, Any], entity: dict[str, Any]) -> dict[str, Any]:
    aggregate: dict[str, Any] = {"fn": item.get("fn", "count")}
    if item.get("field") and aggregate["fn"] != "count":
        aggregate["field"] = item["field"]
    if item.get("groupBy"):
        aggregate["groupBy"] = item["groupBy"]
    if item.get("period"):
        aggregate["period"] = item["period"]
        aggregate["dateField"] = item.get("dateField") or _date_field(entity)
    if item.get("filter"):
        aggregate["filters"] = dict(item["filter"])
    return aggregate


def _same(existing: dict[str, Any], wanted: dict[str, Any], any_date: bool) -> bool:
    """`any_date`: the dashboard item named no date, so the BackendSpec's own aggregate decides which one."""
    keys = ("fn", "field", "groupBy", "period", "filters") + (() if any_date else ("dateField",))
    return all((existing.get(key) or None) == (wanted.get(key) or None) for key in keys)


def _aggregate_id(entity: str, aggregate: dict[str, Any], default_date: str | None = None) -> str:
    """`task.countByStatus`, `reviewLog.countThisWeek`, `plant.countThisDayOnNextWateringDate`,
    `task.countWhereStatusTodo`."""
    name = aggregate["fn"] + (to_pascal(aggregate["field"]) if aggregate.get("field") else "")
    if aggregate.get("groupBy"):
        name += "By" + to_pascal(aggregate["groupBy"])
    if aggregate.get("period"):
        name += "This" + to_pascal(aggregate["period"])
        if aggregate.get("dateField") and aggregate["dateField"] != default_date:
            name += "On" + to_pascal(aggregate["dateField"])
    for key, value in sorted((aggregate.get("filters") or {}).items()):
        words = "".join(ch for ch in str(value).title() if ch.isalnum())
        name += "Where" + to_pascal(key) + (words or "Value")
    return f"{to_camel(entity)}.{name}"


def ensure_aggregates(
    backend: dict[str, Any], outline: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """The aggregate operations the outline's dashboard names, added to the BackendSpec (templated like CRUD, no
    engine); aggregates the BackendSpec has that no dashboard item names join the dashboard. Returns the BackendSpec,
    the outline and notes; an item whose operation would make the BackendSpec invalid is dropped with a note."""
    entities = {entity["name"]: entity for entity in backend.get("entities") or []}
    operations = list(backend.get("operations") or [])
    dashboard: list[dict[str, Any]] = []
    notes: list[dict[str, Any]] = []
    used: set[str] = set()
    for index, item in enumerate(outline.get("dashboard") or []):
        entity = entities[item["entity"]]
        aggregate = _aggregate(item, entity)
        if aggregate.get("period") and not aggregate.get("dateField"):
            notes.append(_note(f"/app/dashboard/{index}", f"{item['entity']} has no date for '{item['label']}'"))
            continue
        found = next(
            (
                op
                for op in operations
                if op.get("type") == "aggregate"
                and op.get("entity") == item["entity"]
                and _same(op.get("aggregate") or {}, aggregate, not item.get("dateField"))
            ),
            None,
        )
        if found is None:
            op_id = _aggregate_id(item["entity"], aggregate, _date_field(entity))
            table = to_kebab(pluralize(item["entity"]))
            found = {
                "operationId": op_id,
                "type": "aggregate",
                "entity": item["entity"],
                "method": "GET",
                "path": f"/{table}/aggregate/{to_kebab(op_id.split('.', 1)[1])}",
                "summary": item["label"],
                "aggregate": aggregate,
            }
            trial = {**backend, "operations": [*operations, found]}
            if not validate_spec_data(trial).report.valid or any(op["operationId"] == op_id for op in operations):
                notes.append(_note(f"/app/dashboard/{index}", f"'{item['label']}' cannot be computed; left out"))
                continue
            operations.append(found)
            notes.append(_note(f"/app/dashboard/{index}", f"'{item['label']}' is computed by {op_id} (added)"))
        used.add(found["operationId"])
        dashboard.append({**item, "operationId": found["operationId"]})
    for op in operations:  # every aggregate on a screen (coverage by construction)
        if op.get("type") != "aggregate" or op["operationId"] in used or op.get("entity") not in entities:
            continue
        aggregate = op.get("aggregate") or {}
        label = op.get("summary") or humanize(op["operationId"].split(".", 1)[1])
        dashboard.append(
            {
                "label": label[:80],
                "kind": "bar" if aggregate.get("groupBy") else "figure",
                "entity": op["entity"],
                "fn": aggregate.get("fn", "count"),
                "operationId": op["operationId"],
                **({"groupBy": aggregate["groupBy"]} if aggregate.get("groupBy") else {}),
            }
        )
        used.add(op["operationId"])
    return {**backend, "operations": operations}, {**outline, "dashboard": dashboard}, notes


# -- the planner ------------------------------------------------------------------------------------------------------


class _Screens:
    def __init__(self, backend: dict[str, Any], outline: dict[str, Any], contract: dict[str, Any]):
        self.backend, self.outline, self.contract = backend, outline, contract
        self.operations = contract_operations(contract)
        self.spec_ops = {op["operationId"]: op for op in backend.get("operations") or []}
        self.entities = {entity["name"]: entity for entity in backend.get("entities") or []}
        self.info = ((contract.get("x-bga") or {}).get("entities")) or {}
        self.pages: list[dict[str, Any]] = []
        self.forms: list[dict[str, Any]] = []
        self.nav: list[dict[str, Any]] = []
        self.assumptions: list[dict[str, Any]] = []
        self.unresolved: list[dict[str, Any]] = []
        self.placed: set[str] = set()
        self.crud: dict[str, dict[str, str]] = {name: {} for name in self.entities}
        self.custom: dict[str, list[str]] = {name: [] for name in self.entities}
        for op in backend.get("operations") or []:
            entity = op.get("entity")
            if entity not in self.entities or op["operationId"] not in self.operations:
                continue
            if op.get("type") == "crud" and op.get("action"):
                self.crud[entity].setdefault(op["action"], op["operationId"])
            elif op.get("type") == "custom":
                self.custom[entity].append(op["operationId"])

    # -- names and lookups

    def slug(self, entity: str) -> str:
        return to_kebab(pluralize(entity))

    def shown(self, entity: str) -> dict[str, Any]:
        return (self.outline.get("entities") or {}).get(entity) or {}

    def label(self, entity: str) -> str:
        return self.shown(entity).get("label") or humanize(entity)

    def plural(self, entity: str) -> str:
        return self.shown(entity).get("plural") or pluralize(self.label(entity))

    def references(self, entity: str) -> list[dict[str, Any]]:
        return list((self.info.get(entity) or {}).get("references") or [])

    def parent_of(self, entity: str) -> dict[str, Any] | None:
        """The first parent this entity is listed under (a required reference with a filter on the list)."""
        list_op = self.crud[entity].get("list")
        filters = self.query_params(list_op) if list_op else {}
        required = self.required_inputs(self.crud[entity].get("create"))
        for reference in self.references(entity):
            parent = reference["entity"]
            if reference["field"] in filters and parent in self.entities and "get" in self.crud[parent]:
                if not required or reference["field"] in required:
                    return reference
        return None

    def route_parent(self, entity: str) -> dict[str, Any] | None:
        """The parent a new record takes from the route: the one it is listed under, else the first required
        reference whose parent has a page (`cartItem.create` from a product's page)."""
        parent = self.parent_of(entity)
        if parent:
            return parent
        required = self.required_inputs(self.crud[entity].get("create"))
        return next(
            (
                ref
                for ref in self.references(entity)
                if ref["field"] in required and ref["entity"] in self.entities and "get" in self.crud[ref["entity"]]
            ),
            None,
        )

    def children_of(self, entity: str) -> list[tuple[str, dict[str, Any]]]:
        return [(name, ref) for name in self.entities if (ref := self.parent_of(name)) and ref["entity"] == entity]

    def query_params(self, op_id: str | None) -> dict[str, dict[str, Any]]:
        operation = self.operations[op_id]["operation"] if op_id else {}
        return {p["name"]: p for p in operation.get("parameters") or [] if p.get("in") == "query"}

    def path_params(self, op_id: str) -> list[str]:
        operation = self.operations[op_id]["operation"]
        return [p["name"] for p in operation.get("parameters") or [] if p.get("in") == "path"]

    def required_query(self, op_id: str) -> list[str]:
        return [name for name, p in self.query_params(op_id).items() if p.get("required")]

    def request(self, op_id: str | None) -> tuple[dict[str, Any], set[str]]:
        if not op_id:
            return {}, set()
        operation = self.operations[op_id]["operation"]
        body = (operation.get("requestBody") or {}).get("content", {}).get("application/json", {})
        schema = resolve(self.contract, body.get("schema") or {})
        return schema.get("properties") or {}, set(schema.get("required") or [])

    def required_inputs(self, op_id: str | None) -> set[str]:
        return self.request(op_id)[1]

    def response_fields(self, op_id: str) -> list[str]:
        record = _response_record(self.contract, self.operations[op_id]["operation"])
        return list(record.get("properties") or {})

    def op_label(self, op_id: str) -> str:
        summary = (self.spec_ops.get(op_id) or {}).get("summary")
        if isinstance(summary, str) and 0 < len(summary) <= 40:
            summary = summary.removeprefix("List ").removeprefix("list ").removeprefix("Get ").strip() or summary
            return summary[:1].upper() + summary[1:]
        name = op_id.split(".", 1)[1]
        entity = (self.spec_ops.get(op_id) or {}).get("entity")
        if name.startswith("list") and len(name) > 4 and entity in self.entities:  # `listDue` → `Due cards`
            return f"{humanize(name[4:])} {self.plural(entity).lower()}"
        return humanize(name)

    def place(self, op_id: str | None) -> None:
        if op_id:
            self.placed.add(op_id)

    # -- forms

    def form_fields(
        self, entity: str, op_id: str, hidden: dict[str, str] | None = None, readable: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """The request's fields as a form; `hidden` fields take a fixed value (`$route.id`), references without one
        are left out (a picker comes with Story 22.6), and `readable` limits an edit form to what `get` returns."""
        properties, required = self.request(op_id)
        hidden = hidden or {}
        shown = self.shown(entity)
        references = {ref["field"] for ref in self.references(entity)}
        fields = []
        for name, prop in properties.items():
            meta = prop.get("x-bga") or {}
            if meta.get("source") in SKIPPED_SOURCES:
                continue
            if name in hidden:
                fields.append({"name": name, "type": "string", "hidden": True, "value": hidden[name], "required": True})
                continue
            reference = name in references or meta.get("source") == "reference"
            if reference and name in required and readable is None and op_id == self.crud[entity].get("create"):
                # a second parent the route cannot give: typed for now, a picker with Story 22.6
                fields.append(self.form_field(entity, name, resolve(self.contract, prop), True, shown))
                self.unresolved.append(
                    _note("/forms", f"{self.label(entity)}: '{name}' is typed as an id until pickers (22.6)")
                )
                continue
            if reference or (readable and name not in readable):
                continue
            fields.append(self.form_field(entity, name, resolve(self.contract, prop), name in required, shown))
        return fields

    def form_field(
        self, entity: str, name: str, schema: dict[str, Any], required: bool, shown: dict[str, Any]
    ) -> dict[str, Any]:
        types = schema.get("type") if isinstance(schema.get("type"), list) else [schema.get("type")]
        for option in schema.get("anyOf") or []:
            types.append(option.get("type"))
            schema = {**option, **schema} if option.get("type") != "null" else schema
        backend_type = next(
            (f.get("type") for f in self.entities[entity].get("fields") or [] if f["name"] == name), None
        )
        enum = [value for value in schema.get("enum") or [] if value is not None]
        kind = "string"
        if enum:
            kind = "enum"
        elif schema.get("format") == "date-time":
            kind = "datetime"
        elif schema.get("format") == "date":
            kind = "date"
        elif "boolean" in types:
            kind = "boolean"
        elif "integer" in types:
            kind = "integer"
        elif "number" in types:
            kind = "number"
        elif backend_type == "text" or (backend_type is None and (schema.get("maxLength") or 0) > 255):
            kind = "text"
        out: dict[str, Any] = {
            "name": name,
            "type": kind,
            "label": (shown.get("fieldLabels") or {}).get(name) or humanize(name),
            "required": required,
        }
        if enum:
            out["values"] = enum
        for key, target in (("minimum", "min"), ("maximum", "max"), ("maxLength", "maxLength")):
            if schema.get(key) is not None:
                out[target] = schema[key]
        return out

    def add_form(self, form: dict[str, Any]) -> str | None:
        if not form["fields"]:
            return None
        self.forms.append(form)
        self.place(form.get("operationId"))
        self.place((form.get("load") or {}).get("operationId"))
        return form["id"]

    # -- sections

    def record_actions(self, entity: str, record: str, detail: bool) -> list[dict[str, Any]]:
        """Actions on one record (`$record` in a list, `$route` on its page): view, edit, delete, custom ones."""
        crud, label, slug = self.crud[entity], self.label(entity), self.slug(entity)
        actions: list[dict[str, Any]] = []
        if not detail and "get" in crud:
            actions.append(
                {"id": "view", "label": "View", "kind": "link", "page": f"{slug}-id", "params": {"id": record}}
            )
        if "update" in crud:
            actions.append(
                {"id": "edit", "label": "Edit", "kind": "link", "page": f"{slug}-id-edit", "params": {"id": record}}
            )
        for op_id in self.custom[entity]:
            found = self.operations[op_id]
            if found["method"] == "GET" or self.path_params(op_id) != ["id"] or self.required_query(op_id):
                continue
            properties, _ = self.request(op_id)
            if properties and not detail:
                continue  # a body opens a dialog: on the record's page only
            action: dict[str, Any] = {
                "id": to_kebab(op_id.split(".", 1)[1]),
                "label": self.op_label(op_id),
                "kind": "mutation",
                "operationId": op_id,
                "params": {"id": record},
                "onSuccess": {"toast": f"{self.op_label(op_id)}: done"},
            }
            if properties:
                form_id = self.add_form(
                    {
                        "id": f"{to_camel(entity)}_{op_id.split('.', 1)[1]}",
                        "operationId": op_id,
                        "params": {"id": "$route.id"},
                        "fields": self.form_fields(entity, op_id),
                        "submitLabel": self.op_label(op_id),
                        "onSuccess": {"toast": f"{self.op_label(op_id)}: done"},
                    }
                )
                if form_id is None:
                    continue
                action["form"] = form_id
            if found["method"] == "DELETE":
                action["confirm"] = f"{self.op_label(op_id)} this {label.lower()}?"
            self.place(op_id)
            actions.append(action)
        if "delete" in crud:
            delete: dict[str, Any] = {
                "id": "delete",
                "label": "Delete",
                "kind": "mutation",
                "operationId": crud["delete"],
                "params": {"id": record},
                "confirm": f"Delete this {label.lower()}? This cannot be undone.",
                "variant": "destructive",
                "onSuccess": {"toast": f"{label} deleted"},
            }
            if detail and "list" in crud:
                delete["onSuccess"]["navigate"] = slug
            actions.append(delete)
            self.place(crud["delete"])
        return actions

    def list_section(
        self,
        entity: str,
        op_id: str,
        section_id: str,
        params: dict[str, Any] | None = None,
        **content: Any,
    ) -> dict[str, Any]:
        shown = self.shown(entity)
        available = self.response_fields(op_id)
        skip = set((params or {}).keys())
        fields = [f for f in shown.get("listFields") or [] if f in available and f not in skip]
        query = self.query_params(op_id)
        references = {ref["field"] for ref in self.references(entity)}
        controls: dict[str, Any] = {}
        if "q" in query:
            controls["search"] = True
        filters = [name for name in query if name not in LIST_CONTROLS and name not in references and name not in skip]
        if filters:
            controls["filters"] = filters
        sort_enum = resolve(self.contract, (query.get("sort") or {}).get("schema") or {}).get("enum") or []
        sort = [value for value in sort_enum if not str(value).startswith("-")]
        if sort:
            controls["sort"] = sort
        self.place(op_id)
        return {
            "id": section_id,
            "component": "AppList",
            "data": {"operationId": op_id, **({"params": params} if params else {}), "fields": fields},
            "content": {
                "entity": entity,
                "title": self.plural(entity),
                "style": shown.get("listStyle") or "table",
                **({"controls": controls} if controls else {}),
                "actions": self.record_actions(entity, "$record.id", detail=False),
                **content,
            },
        }

    # -- pages

    def page(self, page_id: str, route: str, title: str, sections: list[dict[str, Any]]) -> None:
        self.pages.append({"id": page_id, "route": route, "title": title[:120], "sections": sections})

    def entity_pages(self, entity: str) -> None:
        crud, slug, label, plural = self.crud[entity], self.slug(entity), self.label(entity), self.plural(entity)
        parent = self.route_parent(entity)
        # create from the entity's own list: not for a child that needs its parent (it is created from there)
        standalone_create = "create" in crud and parent is None
        list_sections: list[dict[str, Any]] = []
        list_sections += self.collection_sections(entity)
        if "list" in crud:
            create = {"create": {"page": f"{slug}-new", "label": f"New {label.lower()}"}} if standalone_create else {}
            list_sections.append(self.list_section(entity, crud["list"], f"{slug}-list", **create))
        if list_sections:
            self.page(slug, f"/{slug}", plural, list_sections)
        if standalone_create:
            after = f"{slug}-id" if "get" in crud else slug if list_sections else "home"
            self.create_page(entity, f"{slug}-new", f"/{slug}/new", {}, after)
        if parent and "create" in crud and not standalone_create:
            parent_slug = self.slug(parent["entity"])
            self.create_page(
                entity,
                f"{parent_slug}-id-{slug}-new",
                f"/{parent_slug}/[id]/{slug}/new",
                {parent["field"]: "$route.id"},
                f"{parent_slug}-id",
            )
            self.assumptions.append(
                _note("/app", f"{plural} are added from their {self.label(parent['entity']).lower()}'s page")
            )
        if "get" in crud:
            self.detail_page(entity)
        if "update" in crud:
            self.edit_page(entity)

    def create_page(self, entity: str, page_id: str, route: str, hidden: dict[str, str], after: str) -> None:
        label, op_id = self.label(entity), self.crud[entity]["create"]
        suffix = "" if not hidden else f"_in_{to_camel(self.route_parent(entity)['entity'])}"  # type: ignore[index]
        form_id = self.add_form(
            {
                "id": f"{to_camel(entity)}_create{suffix}",
                "operationId": op_id,
                "fields": self.form_fields(entity, op_id, hidden),
                "submitLabel": f"Create {label.lower()}",
                "onSuccess": {"toast": f"{label} created", "navigate": after},
            }
        )
        if form_id:
            section = {"id": f"{to_kebab(form_id)}-form", "component": "AppForm", "form": form_id}
            self.page(page_id, route, f"New {label.lower()}", [{**section, "content": {"entity": entity}}])

    def edit_page(self, entity: str) -> None:
        crud, slug, label = self.crud[entity], self.slug(entity), self.label(entity)
        form: dict[str, Any] = {
            "id": f"{to_camel(entity)}_update",
            "operationId": crud["update"],
            "params": {"id": "$route.id"},
        }
        if "get" in crud:  # loaded from the record; without `get` the form starts empty (a partial update)
            form["load"] = {"operationId": crud["get"], "params": {"id": "$route.id"}}
        readable = self.response_fields(crud["get"]) if "get" in crud else None
        after = f"{slug}-id" if "get" in crud else slug
        form |= {
            "fields": self.form_fields(entity, crud["update"], readable=readable),
            "submitLabel": "Save changes",
            "onSuccess": {"toast": f"{label} saved", "navigate": after},
        }
        form_id = self.add_form(form)
        if form_id:
            section = {
                "id": f"{slug}-edit-form",
                "component": "AppForm",
                "form": form_id,
                "content": {"entity": entity},
            }
            self.page(f"{slug}-id-edit", f"/{slug}/[id]/edit", f"Edit {label.lower()}", [section])

    def detail_page(self, entity: str) -> None:
        crud, slug, label = self.crud[entity], self.slug(entity), self.label(entity)
        available = self.response_fields(crud["get"])
        shown = self.shown(entity)
        sections = [
            {
                "id": f"{slug}-detail",
                "component": "AppDetail",
                "data": {
                    "operationId": crud["get"],
                    "params": {"id": "$route.id"},
                    "fields": [f for f in shown.get("detailFields") or [] if f in available],
                },
                "content": {
                    "entity": entity,
                    "title": label,
                    "actions": self.record_actions(entity, "$route.id", detail=True),
                },
            }
        ]
        self.place(crud["get"])
        for op_id in self.custom[entity]:  # a record's own summary (`deck.stats`)
            found = self.operations[op_id]
            action = (found["operation"].get("x-bga") or {}).get("action")
            if found["method"] == "GET" and action != "list" and self.path_params(op_id) == ["id"]:
                if not self.required_query(op_id):
                    sections.append(
                        {
                            "id": to_kebab(op_id.replace(".", "-")),
                            "component": "AppDetail",
                            "data": {"operationId": op_id, "params": {"id": "$route.id"}},
                            "content": {"entity": entity, "title": self.op_label(op_id), "variant": "summary"},
                        }
                    )
                    self.place(op_id)
        listed = {child for child, _ in self.children_of(entity)}
        for child in self.entities:  # children created here but not listed here (`cartItem` on a product)
            reference = self.route_parent(child)
            if child in listed or not reference or reference["entity"] != entity or "create" not in self.crud[child]:
                continue
            sections[0]["content"]["actions"].insert(
                0,
                {
                    "id": f"add-{self.slug(child)}",
                    "label": f"Add {self.label(child).lower()}",
                    "kind": "link",
                    "page": f"{slug}-id-{self.slug(child)}-new",
                    "params": {"id": "$route.id"},
                },
            )
        for child, reference in self.children_of(entity):
            child_slug, child_crud = self.slug(child), self.crud[child]
            create = {}
            if (
                "create" in child_crud
                and child_crud["create"]
                and reference["field"] in self.required_inputs(child_crud["create"])
            ):
                create = {
                    "create": {
                        "page": f"{slug}-id-{child_slug}-new",
                        "label": f"Add {self.label(child).lower()}",
                        "params": {"id": "$route.id"},
                    }
                }
            elif "create" in child_crud:
                create = {"create": {"page": f"{child_slug}-new", "label": f"Add {self.label(child).lower()}"}}
            sections.append(
                self.list_section(
                    child,
                    child_crud["list"],
                    f"{child_slug}-tab",
                    {reference["field"]: "$route.id"},
                    tab=self.plural(child),
                    **create,
                )
            )
            for op_id in self.custom[child]:  # a child's own lists that filter by this parent (`card.listDue`)
                found = self.operations[op_id]
                if (found["operation"].get("x-bga") or {}).get("action") != "list" or found["method"] != "GET":
                    continue
                if self.path_params(op_id) or reference["field"] not in self.query_params(op_id):
                    continue
                if set(self.required_query(op_id)) - {reference["field"]}:
                    continue
                section = self.list_section(
                    child,
                    op_id,
                    to_kebab(op_id.replace(".", "-")) + "-tab",
                    {reference["field"]: "$route.id"},
                    tab=self.op_label(op_id),
                )
                section["content"]["title"] = self.op_label(op_id)
                sections.append(section)
        self.page(f"{slug}-id", f"/{slug}/[id]", label, sections)

    def collection_sections(self, entity: str) -> list[dict[str, Any]]:
        """The entity's custom operations on the whole collection, on its list page: summaries and buttons. Custom
        lists that no parent tab shows get pages of their own (`custom_list_pages`)."""
        sections: list[dict[str, Any]] = []
        actions: list[dict[str, Any]] = []
        for op_id in self.custom[entity]:
            found = self.operations[op_id]
            if self.path_params(op_id) or self.required_query(op_id):
                continue
            action = (found["operation"].get("x-bga") or {}).get("action")
            if found["method"] == "GET" and action != "list":
                sections.append(
                    {
                        "id": to_kebab(op_id.replace(".", "-")),
                        "component": "AppDetail",
                        "data": {"operationId": op_id},
                        "content": {"entity": entity, "title": self.op_label(op_id), "variant": "summary"},
                    }
                )
                self.place(op_id)
            elif found["method"] != "GET":
                properties, _ = self.request(op_id)
                item: dict[str, Any] = {
                    "id": to_kebab(op_id.split(".", 1)[1]),
                    "label": self.op_label(op_id),
                    "kind": "mutation",
                    "operationId": op_id,
                    "onSuccess": {"toast": f"{self.op_label(op_id)}: done"},
                }
                if properties:
                    form_id = self.add_form(
                        {
                            "id": f"{to_camel(entity)}_{op_id.split('.', 1)[1]}",
                            "operationId": op_id,
                            "fields": self.form_fields(entity, op_id),
                            "submitLabel": self.op_label(op_id),
                            "onSuccess": {"toast": f"{self.op_label(op_id)}: done"},
                        }
                    )
                    if form_id is None:
                        continue
                    item["form"] = form_id
                if found["method"] == "DELETE":
                    item["confirm"] = f"{self.op_label(op_id)}?"
                actions.append(item)
                self.place(op_id)
        if actions:
            sections.append(
                {
                    "id": f"{self.slug(entity)}-actions",
                    "component": "AppActions",
                    "content": {"entity": entity, "actions": actions},
                }
            )
        return sections

    def custom_list_pages(self) -> None:
        """Custom lists no parent shows (`card.listDue` without a deck): a page of their own in the navigation."""
        routes = {page["route"] for page in self.pages}
        for entity in self.entities:
            for op_id in self.custom[entity]:
                found = self.operations[op_id]
                if (found["operation"].get("x-bga") or {}).get("action") != "list" or found["method"] != "GET":
                    continue
                if self.path_params(op_id) or self.required_query(op_id):
                    continue
                slug = self.slug(entity)
                tail = [part for part in found["path"].split("/") if part and not part.startswith("{")][-1]
                name = to_kebab(tail) if tail != slug else to_kebab(op_id.split(".", 1)[1])
                route = f"/{slug}/{name}" if name not in ("new", slug) else f"/{slug}/{to_kebab(op_id.split('.')[1])}"
                if route in routes:
                    continue
                page_id = f"{slug}-{name}"
                section = self.list_section(entity, op_id, f"{to_kebab(op_id.replace('.', '-'))}-list")
                section["content"]["title"] = self.op_label(op_id)
                self.page(page_id, route, self.op_label(op_id), [section])
                self.nav.append({"label": self.op_label(op_id)[:40], "page": page_id, "entity": entity})
                routes.add(route)

    def dashboard(self, name: str) -> list[dict[str, Any]]:
        sections: list[dict[str, Any]] = []
        for index, item in enumerate(self.outline.get("dashboard") or []):
            op_id = item.get("operationId")
            if op_id not in self.operations:
                continue
            content = {key: item[key] for key in ("label", "kind", "entity", "groupBy", "fn", "field") if item.get(key)}
            sections.append(
                {
                    "id": f"figure-{index + 1}",
                    "component": "AppDashboard",
                    "data": {"operationId": op_id},
                    "content": content,
                }
            )
            self.place(op_id)
        recent = [
            item["entity"] for item in self.outline.get("nav") or [] if "list" in self.crud.get(item["entity"], {})
        ]
        for entity in recent[:RECENT_LISTS]:
            op_id = self.crud[entity]["list"]
            params: dict[str, Any] = {}
            if "limit" in self.query_params(op_id):
                params["limit"] = RECENT
            sort_enum = resolve(self.contract, (self.query_params(op_id).get("sort") or {}).get("schema") or {})
            newest = next((v for v in sort_enum.get("enum") or [] if v in ("-createdAt", "-updatedAt")), None)
            if newest:
                params["sort"] = newest
            section = self.list_section(entity, op_id, f"recent-{self.slug(entity)}", params or None, variant="recent")
            section["content"]["title"] = f"Recent {self.plural(entity).lower()}"
            section["data"]["fields"] = section["data"]["fields"][:3]
            sections.append(section)
        if not sections:
            sections.append({"id": "dashboard", "component": "AppDashboard", "content": {"label": name}})
        return sections

    def reach_every_page(self) -> None:
        """An entity's list (or create-only page) that neither the navigation nor a parent's page links to joins
        the navigation, so no screen is reachable only by its address."""
        in_nav = {item["page"] for item in self.nav}
        pages = {page["id"] for page in self.pages}
        for entity in self.entities:
            if self.parent_of(entity):
                continue
            slug = self.slug(entity)
            if slug in pages and slug not in in_nav:
                self.nav.append({"label": self.plural(entity), "page": slug, "entity": entity})
                self.assumptions.append(
                    _note("/layout/header/navigation", f"{self.plural(entity)} joined the navigation")
                )
            elif slug not in pages and f"{slug}-new" in pages and f"{slug}-new" not in in_nav:
                label = f"New {self.label(entity).lower()}"
                self.nav.append({"label": label, "page": f"{slug}-new", "entity": entity})

    def build(self, name: str) -> list[dict[str, Any]]:
        for entity in self.entities:
            self.entity_pages(entity)
        self.custom_list_pages()
        home = self.outline.get("home") or "dashboard"
        listed = {page["id"] for page in self.pages}
        nav = []
        for item in self.outline.get("nav") or []:
            page = self.slug(item["entity"])
            if page in listed:
                nav.append(
                    {"label": item.get("label") or self.plural(item["entity"]), "page": page, "entity": item["entity"]}
                )
        if home != "dashboard" and self.slug(home) in listed:
            home_page = next(page for page in self.pages if page["id"] == self.slug(home))
            self.page("home", "/", home_page["title"], [dict(section) for section in home_page["sections"]])
        else:
            self.page("home", "/", name, self.dashboard(name))
            nav.insert(0, {"label": "Dashboard", "page": "home"})
        self.nav = nav + self.nav
        self.reach_every_page()
        self.pages.sort(key=lambda page: (page["route"] != "/", page["route"]))
        return self.pages


def app_frontend_spec(
    backend: dict[str, Any], outline: dict[str, Any], theme: dict[str, Any], contract: dict[str, Any] | None = None
) -> AppScreens:
    """The FrontendSpec of an app (a dict, as the draft stores it) from the completed outline, the BackendSpec (with
    the dashboard's aggregates already added, `ensure_aggregates`) and its contract."""
    project = backend.get("project") or {}
    name = outline.get("name") or project.get("name") or "App"
    app = {key: value for key, value in outline.items() if key != "dashboard"} | {"name": name}
    app["dashboard"] = [
        {key: v for key, v in item.items() if key != "operationId"} for item in outline.get("dashboard") or []
    ]
    if contract is None:  # an empty shell (Story 22.1)
        pages = [
            {
                "id": "home",
                "route": "/",
                "title": name,
                "sections": [{"id": "dashboard", "component": "AppDashboard", "content": {"label": name}}],
            }
        ]
        spec = _spec(name, project, theme, app, pages, [], [])
        return AppScreens(spec)
    screens = _Screens(backend, outline, contract)
    pages = screens.build(name)
    navigation = [{"label": item["label"][:60], "page": item["page"]} for item in screens.nav]
    spec = _spec(name, project, theme, app, pages, screens.forms, navigation)
    for op_id in uncovered_operations(spec, contract):
        found = screens.operations[op_id]
        screens.unresolved.append(
            _note(
                "/pages",
                f"{op_id} ({found['method']} {found['path']}) has no screen: the kit has no place for its parameters",
            )
        )
    return AppScreens(spec, screens.assumptions, screens.unresolved)


def _spec(
    name: str,
    project: dict[str, Any],
    theme: dict[str, Any],
    app: dict[str, Any],
    pages: list[dict[str, Any]],
    forms: list[dict[str, Any]],
    navigation: list[dict[str, Any]],
) -> dict[str, Any]:
    spec: dict[str, Any] = {
        "specVersion": SPEC_VERSION,
        "project": {"name": name, "mode": "dynamic", "flow": "app", **_description(project)},
        "theme": theme,
        "layout": {"shell": "sidebar", "header": {"logoText": name, "navigation": navigation}},
        "app": app,
        "pages": pages,
    }
    if forms:
        spec["forms"] = forms
    return spec


def _description(project: dict[str, Any]) -> dict[str, Any]:
    return {"description": project["description"]} if project.get("description") else {}
