from typing import Any

from .naming import table_name, to_camel, to_kebab
from .schema_v1 import BackendSpecV1, Pagination


def default_foreign_key(parent_entity: str) -> str:
    return f"{to_camel(parent_entity)}Id"


def normalize_spec(spec: BackendSpecV1) -> dict[str, Any]:
    """Fills implicit defaults so later stages (planner, prompts, manifest) never re-derive them."""
    normalized = spec.model_copy(deep=True)
    normalized.project.slug = normalized.project.slug or to_kebab(normalized.project.name)
    for entity in normalized.entities:
        entity.table = entity.table or table_name(entity.name)
        for field in entity.fields:
            if field.nullable is None:
                field.nullable = not (field.required or field.primary)
    for relationship in normalized.relationships:
        if relationship.type != "many-to-many" and relationship.foreign_key is None:
            relationship.foreign_key = default_foreign_key(relationship.from_)
    for operation in normalized.operations:
        operation.auth = operation.auth or "none"
        if operation.action == "list" and operation.pagination in (None, True):
            operation.pagination = Pagination()
        elif operation.pagination is False:
            operation.pagination = None
    return normalized.model_dump(by_alias=True, mode="json", exclude_none=True)
