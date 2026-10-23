"""Deterministic Frontend-Agent site JSON → BackendSpec draft (Story 2.5).

Data-bound components on the pages decide which operations exist and what they support; collection records
become seed data. Anything the importer cannot decide safely becomes an assumption or an unresolved item.
"""

import re
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel

from src.modules.shared.domain.backend_spec import ValidationReport, validate_spec_data
from src.modules.shared.domain.backend_spec.naming import pluralize, singularize, to_camel, to_kebab, to_pascal

_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ISO_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}")
_MAX_DEPTH = 200

CONTAINERS = {"CollectionBrowser": "list", "CollectionStrip": "list", "CollectionDetail": "get"}
LIST_CONTROLS = {"CategoryFilter", "SortControl", "SearchBox", "Pagination", "ResultCount"}
FIELD_READERS = {"RecordField", "RecordImage", "RecordEach"}
RENDER_HELPERS = {"ItemList", "EachValue"}
KNOWN_DATA_COMPONENTS = set(CONTAINERS) | LIST_CONTROLS | FIELD_READERS | RENDER_HELPERS | {"RecordLink"}
_DATA_COMPONENT_NAME = re.compile(r"^(Collection|Record|Each)[A-Z]")

CATEGORY_LIKE = {"category", "status", "type", "kind", "genre", "section"}
PERSON_LIKE = {"author", "owner", "creator", "writer", "user", "editor"}
ASSET_LIKE = re.compile(r"(image|photo|thumbnail|avatar|cover|picture)", re.IGNORECASE)
PRESENTATION_PROPS = {"className", "style", "animate", "children"}


class FrontendImportError(ValueError):
    pass


class ImportNote(BaseModel):
    path: str
    message: str
    suggestion: str | None = None


class FrontendImportResult(BaseModel):
    backend_spec: dict[str, Any]
    seed: list[dict[str, Any]]
    assumptions: list[ImportNote]
    unresolved: list[ImportNote]
    bindings: list[dict[str, Any]]
    validation: ValidationReport


@dataclass
class _Collection:
    index: int
    key: str
    entity: str
    resource_path: str
    fields: list[dict[str, Any]]
    field_names: dict[str, str]
    records: list[dict[str, Any]]
    page_size: int | None = None
    sort: list[str] = field(default_factory=list)
    search: list[str] = field(default_factory=list)
    filters: list[str] = field(default_factory=list)
    related_by: list[str] = field(default_factory=list)
    used_fields: set[str] = field(default_factory=set)
    referenced: bool = False

    @property
    def op_prefix(self) -> str:
        return to_camel(self.entity)

    @property
    def pk(self) -> str:
        return next(f["name"] for f in self.fields if f.get("primary"))

    def has_field(self, name: str) -> bool:
        return name in self.field_names.values()


def import_frontend_site(site: Any, include_admin_crud: bool = True) -> FrontendImportResult:
    return _Importer(site, include_admin_crud).run()


class _Importer:
    def __init__(self, site: Any, include_admin_crud: bool):
        if not isinstance(site, dict) or not isinstance(site.get("collections"), list):
            raise FrontendImportError("Site JSON must be an object with a 'collections' array")
        if not isinstance(site.get("pages", []), list):
            raise FrontendImportError("'pages' must be an array")
        self.site = site
        self.include_admin_crud = include_admin_crud
        self.assumptions: list[ImportNote] = []
        self.unresolved: list[ImportNote] = []
        self.bindings: list[dict[str, Any]] = []
        self.collections: list[_Collection] = []

    def _assume(self, path: str, message: str, suggestion: str | None = None) -> None:
        self.assumptions.append(ImportNote(path=path, message=message, suggestion=suggestion))

    def _unresolved(self, path: str, message: str) -> None:
        self.unresolved.append(ImportNote(path=path, message=message))

    def run(self) -> FrontendImportResult:
        for index, raw in enumerate(self.site["collections"]):
            collection = self._read_collection(index, raw)
            if collection is not None:
                self.collections.append(collection)
        for p_index, page in enumerate(self.site.get("pages", [])):
            if isinstance(page, dict) and isinstance(page.get("tree"), dict):
                slug = str(page.get("slug") or p_index)
                self._walk(page["tree"], f"/pages/{p_index}/tree", slug, container=None, depth=0)

        operations = [op for collection in self.collections for op in self._operations(collection)]
        seed = [self._seed(collection) for collection in self.collections if collection.records]
        for collection in self.collections:
            self._field_assumptions(collection)
            if not collection.referenced:
                self._assume(
                    f"/collections/{collection.index}",
                    f"Collection '{collection.key}' is not used by any page; list and get operations were still added",
                )

        spec = {
            "specVersion": "1.0",
            "project": {
                "name": str(self.site.get("name") or "Imported site")[:120],
                "description": "Backend generated from a Frontend-Agent site JSON",
            },
            "stack": {"framework": "fastapi", "database": "postgresql", "orm": "sqlmodel", "migration": "alembic"},
            "entities": [{"name": c.entity, "fields": c.fields} for c in self.collections],
            "operations": operations,
            "seed": seed,
            "x-frontendBindings": self.bindings,
        }
        return FrontendImportResult(
            backend_spec=spec,
            seed=seed,
            assumptions=self.assumptions,
            unresolved=self.unresolved,
            bindings=self.bindings,
            validation=validate_spec_data(spec).report,
        )

    def _read_collection(self, index: int, raw: Any) -> _Collection | None:
        path = f"/collections/{index}"
        key = raw.get("key") if isinstance(raw, dict) else None
        records = raw.get("records", []) if isinstance(raw, dict) else None
        if not isinstance(key, str) or not key or not isinstance(records, list):
            self._unresolved(path, "Collection needs a string 'key' and a 'records' array; skipped")
            return None
        records = [record for record in records if isinstance(record, dict)]
        entity = to_pascal(singularize(key)) or f"Collection{index}"
        if any(c.entity == entity for c in self.collections):
            self._unresolved(path, f"Collection '{key}' maps to entity '{entity}', which already exists; skipped")
            return None

        field_names: dict[str, str] = OrderedDict()
        for record in records:
            for raw_name in record:
                if raw_name in field_names:
                    continue
                name = raw_name if _IDENTIFIER.match(raw_name) else to_camel(raw_name)
                if not name or not _IDENTIFIER.match(name) or name in field_names.values():
                    self._unresolved(f"{path}/records", f"Field '{raw_name}' has no usable identifier; skipped")
                    continue
                if name != raw_name:
                    self._assume(f"{path}/records", f"Field '{raw_name}' renamed to '{name}'")
                field_names[raw_name] = name

        fields = [
            self._infer_field(field_names[raw], [r.get(raw) for r in records], len(records), path)
            for raw in field_names
        ]
        fields = self._ensure_primary_key(fields, records, field_names, path)
        resource_path = "/" + to_kebab(pluralize(entity))
        return _Collection(index, key, entity, resource_path, fields, field_names, records)

    def _infer_field(self, name: str, values: list[Any], total: int, path: str) -> dict[str, Any]:
        present = [value for value in values if value is not None]
        definition: dict[str, Any] = {"name": name, "type": "string"}
        if present and len(present) == total:
            definition["required"] = True
        if not present:
            self._assume(path, f"'{name}' has no values; typed as string")
        elif all(isinstance(v, bool) for v in present):
            definition["type"] = "boolean"
        elif all(isinstance(v, int) and not isinstance(v, bool) for v in present):
            definition["type"] = "integer"
        elif all(isinstance(v, int | float) and not isinstance(v, bool) for v in present):
            definition["type"] = "float"
        elif all(isinstance(v, str) for v in present):
            definition.update(self._string_type(present))
        elif all(isinstance(v, list | dict) for v in present):
            definition["type"] = "json"
        else:
            definition["type"] = "json"
            self._assume(path, f"'{name}' mixes value types; stored as json")
        return definition

    @staticmethod
    def _string_type(values: list[str]) -> dict[str, Any]:
        if all(_ISO_DATE.match(v) and _is_date(v) for v in values):
            return {"type": "date"}
        if all(_ISO_DATETIME.match(v) and _is_datetime(v) for v in values):
            return {"type": "datetime"}
        if all(_is_uuid(v) for v in values):
            return {"type": "uuid"}
        if any(len(v) > 255 or "\n" in v for v in values):
            return {"type": "text"}
        return {"type": "string", "maxLength": 255}

    def _ensure_primary_key(self, fields, records, field_names, path) -> list[dict[str, Any]]:
        id_field = next((f for f in fields if f["name"] == "id"), None)
        raw_id = next((raw for raw, name in field_names.items() if name == "id"), None)
        ids = [record.get(raw_id) for record in records] if raw_id else []
        if id_field and all(v is not None for v in ids) and len({repr(v) for v in ids}) == len(ids):
            id_field["primary"] = True
            id_field.pop("required", None)
            id_field.pop("maxLength", None)
            if id_field["type"] not in ("uuid", "integer"):
                id_field["type"] = "string"
                id_field["maxLength"] = 64
                self._assume(
                    f"{path}/records",
                    "Existing ids are not UUIDs; kept as a string primary key so frontend links keep working",
                )
            return fields
        if id_field:
            self._unresolved(f"{path}/records", "'id' values are missing or not unique; replaced by a generated uuid")
            fields = [f for f in fields if f["name"] != "id"]
        else:
            self._assume(f"{path}/records", "Records have no 'id'; added a generated uuid primary key")
        return [{"name": "id", "type": "uuid", "primary": True}, *fields]

    def _walk(self, node: Any, path: str, page: str, container: tuple | None, depth: int) -> None:
        if depth > _MAX_DEPTH:
            raise FrontendImportError(f"Page tree is nested deeper than {_MAX_DEPTH} levels at {path}")
        if not isinstance(node, dict):
            return
        component = node.get("type")
        props = node.get("props") if isinstance(node.get("props"), dict) else {}
        if isinstance(component, str):
            container = self._visit(component, props, path, page, container)
        children = node.get("children")
        if isinstance(children, list):
            for index, child in enumerate(children):
                self._walk(child, f"{path}/children/{index}", page, container, depth + 1)
        elif isinstance(children, dict):
            self._walk(children, f"{path}/children", page, container, depth + 1)

    def _visit(self, component: str, props: dict, path: str, page: str, container: tuple | None):
        if component not in KNOWN_DATA_COMPONENTS:
            if _DATA_COMPONENT_NAME.match(component):
                self._unresolved(path, f"Unknown data component '{component}'; no backend operation derived")
            return container
        if component in RENDER_HELPERS:
            return container

        collection = self._collection_for(props, container, path)
        if collection is None:
            return container
        collection.referenced = True

        if component in CONTAINERS:
            return self._visit_container(component, props, path, page, collection)
        if component == "RecordLink":
            self._bind(page, path, component, f"{collection.op_prefix}.get", {"detailSlug": props.get("detailSlug")})
        elif component in LIST_CONTROLS:
            self._visit_list_control(component, props, path, page, collection, container)
        elif component in FIELD_READERS:
            self._visit_field_reader(component, props, path, page, collection, container)
        return container

    def _visit_container(self, component, props, path, page, collection):
        if component == "CollectionDetail":
            self._bind(page, path, component, f"{collection.op_prefix}.get", {})
            return ("get", collection, props)

        params = {k: props[k] for k in ("pageSize", "sortBy", "order", "limit", "like") if k in props}
        if component == "CollectionBrowser":
            if isinstance(props.get("pageSize"), int):
                collection.page_size = props["pageSize"]
            for item in props.get("sortFields") or []:
                name = item.get("field") if isinstance(item, dict) else item
                self._use_field(collection, name, path, collection.sort, component)
            for name in props.get("searchFields") or []:
                self._use_field(collection, name, path, collection.search, component)
            if props.get("categoryField"):
                self._use_field(collection, props["categoryField"], path, collection.filters, component)
            params.update({k: props[k] for k in ("sortFields", "searchFields", "categoryField") if k in props})
        if props.get("sortBy"):
            self._use_field(collection, props["sortBy"], path, collection.sort, component)

        if props.get("like"):
            self._use_field(collection, props["like"], path, collection.related_by, component)
            self._bind(page, path, component, f"{collection.op_prefix}.listRelated", params)
        else:
            self._bind(page, path, component, f"{collection.op_prefix}.list", params)
        return ("list", collection, props)

    def _visit_list_control(self, component, props, path, page, collection, container) -> None:
        if container is None or container[0] != "list":
            self._unresolved(path, f"'{component}' is outside a collection list; ignored")
            return
        if component == "CategoryFilter":
            field_name = container[2].get("categoryField") or props.get("field")
            if not field_name:
                field_name = next((n for n in CATEGORY_LIKE if collection.has_field(n)), None)
                if field_name:
                    self._assume(path, f"CategoryFilter has no field; filtering on '{field_name}'")
            if not field_name:
                self._unresolved(path, "CategoryFilter has no field and no category-like field exists")
                return
            self._use_field(collection, field_name, path, collection.filters, component)
        self._bind(page, path, component, f"{collection.op_prefix}.list", props)

    def _visit_field_reader(self, component, props, path, page, collection, container) -> None:
        field_name = props.get("field") or props.get("altField")
        if field_name and self._use_field(collection, field_name, path, None, component):
            collection.used_fields.add(field_name)

    def _collection_for(self, props: dict, container: tuple | None, path: str) -> _Collection | None:
        wanted = props.get("collection") or props.get("collectionKey") or props.get("collectionId")
        if wanted:
            found = next(
                (c for c in self.collections if wanted in (c.key, self.site["collections"][c.index].get("id"))),
                None,
            )
            if found is None:
                self._unresolved(path, f"Component refers to unknown collection '{wanted}'")
            return found
        if container is not None:
            return container[1]
        if len(self.collections) == 1:
            return self.collections[0]
        self._unresolved(path, "Component does not say which collection it shows")
        return None

    def _use_field(self, collection, name, path, target: list | None, component: str) -> bool:
        if not isinstance(name, str) or not collection.has_field(name):
            self._unresolved(path, f"{component} uses '{name}', which is not a field of {collection.entity}")
            return False
        if target is not None and name not in target:
            target.append(name)
        return True

    def _bind(self, page: str, path: str, component: str, operation_id: str, params: dict) -> None:
        self.bindings.append(
            {
                "page": page,
                "componentPath": path,
                "component": component,
                "operationId": operation_id,
                "params": {
                    k: v
                    for k, v in params.items()
                    if v is not None and k not in PRESENTATION_PROPS and not k.startswith(("data-", "aria-"))
                },
            }
        )

    def _operations(self, c: _Collection) -> list[dict[str, Any]]:
        item_path = f"{c.resource_path}/{{id}}"
        list_op: dict[str, Any] = {
            "operationId": f"{c.op_prefix}.list",
            "type": "crud",
            "action": "list",
            "entity": c.entity,
            "method": "GET",
            "path": c.resource_path,
            "pagination": {"defaultLimit": c.page_size or 20, "maxLimit": 100},
        }
        for key in ("filters", "sort", "search"):
            if getattr(c, key):
                list_op[key] = list(getattr(c, key))
        ops = [
            list_op,
            {
                "operationId": f"{c.op_prefix}.get",
                "type": "crud",
                "action": "get",
                "entity": c.entity,
                "method": "GET",
                "path": item_path,
            },
        ]
        if c.related_by:
            fields = ", ".join(f"`{name}`" for name in c.related_by)
            plural = pluralize(c.entity.lower())
            ops.append(
                {
                    "operationId": f"{c.op_prefix}.listRelated",
                    "type": "custom",
                    "entity": c.entity,
                    "method": "GET",
                    "path": f"{item_path}/related",
                    "summary": f"Related {plural}",
                    "description": f"{plural.capitalize()} sharing {fields} with the given record, excluding it. "
                    "Query parameter `limit` caps the result.",
                }
            )
        if self.include_admin_crud:
            for action, method, path in (
                ("create", "POST", c.resource_path),
                ("update", "PATCH", item_path),
                ("delete", "DELETE", item_path),
            ):
                ops.append(
                    {
                        "operationId": f"{c.op_prefix}.{action}",
                        "type": "crud",
                        "action": action,
                        "entity": c.entity,
                        "method": method,
                        "path": path,
                    }
                )
            self._assume(
                f"/collections/{c.index}",
                f"Added create/update/delete for {c.entity} although the site has no editing UI",
                suggestion="Turn off 'Include admin CRUD' for a read-only API, or protect these with auth (Epic 10)",
            )
        return ops

    def _seed(self, c: _Collection) -> dict[str, Any]:
        rows = [{c.field_names[k]: v for k, v in record.items() if k in c.field_names} for record in c.records]
        return {"entity": c.entity, "records": rows}

    def _field_assumptions(self, c: _Collection) -> None:
        path = f"/collections/{c.index}/records"
        for definition in c.fields:
            name = definition["name"]
            if definition.get("primary"):
                continue
            raw_name = next(raw for raw, mapped in c.field_names.items() if mapped == name)
            values = [r.get(raw_name) for r in c.records if r.get(raw_name) is not None]
            distinct = {repr(v) for v in values}
            lower = name.lower()
            if definition["type"] == "json" and values and all(isinstance(v, list) for v in values):
                self._assume(
                    path,
                    f"'{name}' holds lists; kept inline as a json array",
                    suggestion=f"Model it as a separate {to_pascal(singularize(name))} entity (many-to-many)",
                )
            elif definition["type"] == "string" and lower in PERSON_LIKE:
                self._assume(
                    path,
                    f"'{name}' kept as a plain string ({len(distinct)} distinct values)",
                    suggestion=f"Model it as a separate {to_pascal(name)} entity (one-to-many)",
                )
            elif definition["type"] == "string" and (lower in CATEGORY_LIKE or name in c.filters):
                if 0 < len(distinct) <= 10 and len(distinct) < len(values):
                    definition["index"] = True
                    choices = sorted(str(v) for v in set(values))
                    self._assume(
                        path,
                        f"'{name}' has {len(distinct)} distinct values; kept as an indexed string",
                        suggestion=f"Make it an enum with values {choices}",
                    )
            elif definition["type"] == "string" and ASSET_LIKE.search(name):
                self._assume(path, f"'{name}' holds asset paths; files are not uploaded to the backend")


def _is_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def _is_datetime(value: str) -> bool:
    try:
        datetime.fromisoformat(value)
        return True
    except ValueError:
        return False


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False
