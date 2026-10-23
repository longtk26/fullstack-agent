import json
import re
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from pydantic import ValidationError

from .issues import Severity, SpecIssue, SpecIssueCode, ValidationReport
from .naming import table_name, to_snake
from .normalizer import default_foreign_key, normalize_spec
from .registry import SPEC_MODELS
from .schema_v1 import BackendSpecV1, Entity, FieldDef, Operation

C = SpecIssueCode
_PATH_PARAM = re.compile(r"\{([^}]+)\}")
_ACTION_METHODS = {
    "create": {"POST"},
    "get": {"GET"},
    "list": {"GET"},
    "update": {"PUT", "PATCH"},
    "delete": {"DELETE"},
}
_ITEM_ACTIONS = {"get", "update", "delete"}


@dataclass
class SpecValidationResult:
    report: ValidationReport
    spec: BackendSpecV1 | None = None
    normalized: dict[str, Any] | None = None


def validate_spec_text(raw: str | bytes) -> SpecValidationResult:
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        where = f" (line {exc.lineno}, column {exc.colno})" if isinstance(exc, json.JSONDecodeError) else ""
        issue = SpecIssue(code=C.JSON_MALFORMED, path="", message=f"Body is not valid JSON{where}: {exc}")
        return SpecValidationResult(ValidationReport.from_issues([issue], None))
    return validate_spec_data(data)


def validate_spec_data(data: Any) -> SpecValidationResult:
    if not isinstance(data, dict):
        issue = SpecIssue(code=C.SCHEMA_VIOLATION, path="", message="BackendSpec must be a JSON object")
        return SpecValidationResult(ValidationReport.from_issues([issue], None))

    version = data.get("specVersion")
    model = SPEC_MODELS.get(version) if isinstance(version, str) else None
    if model is None:
        issue = SpecIssue(
            code=C.SPEC_VERSION_UNSUPPORTED,
            path="/specVersion",
            message=f"Unsupported specVersion {version!r}",
            hint=f"Supported versions: {', '.join(SPEC_MODELS)}",
        )
        return SpecValidationResult(ValidationReport.from_issues([issue], None))

    try:
        spec = model.model_validate(data)
    except ValidationError as exc:
        issues = [_schema_issue(error) for error in exc.errors()]
        return SpecValidationResult(ValidationReport.from_issues(issues, version))

    issues = _SemanticChecker(spec).run()
    report = ValidationReport.from_issues(issues, version)
    return SpecValidationResult(report, spec, normalize_spec(spec) if report.valid else None)


def _schema_issue(error: dict[str, Any]) -> SpecIssue:
    path = "".join(f"/{part}" for part in error["loc"])
    message = "Unknown property" if error["type"] == "extra_forbidden" else error["msg"]
    return SpecIssue(code=C.SCHEMA_VIOLATION, path=path, message=message)


def _norm_route(path: str) -> str:
    return _PATH_PARAM.sub("{}", path.rstrip("/") or "/")


def value_matches_type(value: Any, field: FieldDef) -> bool:
    """Shared by defaults and seed rows; `None` is handled by callers (nullability)."""
    kind = field.type
    if kind in ("string", "text"):
        return isinstance(value, str) and (field.max_length is None or len(value) <= field.max_length)
    if kind == "uuid":
        return isinstance(value, str) and _parses(uuid.UUID, value)
    if kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool) and _in_range(value, field)
    if kind in ("float", "decimal"):
        return isinstance(value, int | float) and not isinstance(value, bool) and _in_range(value, field)
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "date":
        return isinstance(value, str) and (value == "now" or _parses(date.fromisoformat, value))
    if kind == "datetime":
        return isinstance(value, str) and (value == "now" or _parses(datetime.fromisoformat, value))
    if kind == "enum":
        return isinstance(value, str) and value in (field.values or [])
    return True


def _parses(parser, value: str) -> bool:
    try:
        parser(value)
        return True
    except ValueError:
        return False


def _in_range(value: float, field: FieldDef) -> bool:
    return (field.min is None or value >= field.min) and (field.max is None or value <= field.max)


class _SemanticChecker:
    def __init__(self, spec: BackendSpecV1):
        self.spec = spec
        self.issues: list[SpecIssue] = []
        self.entities: dict[str, Entity] = {entity.name: entity for entity in spec.entities}
        self.fields: dict[str, dict[str, FieldDef]] = {
            entity.name: {field.name: field for field in entity.fields} for entity in spec.entities
        }
        self.policies = {policy.name: policy for policy in spec.policies}
        self.rule_ids = {rule.id for rule in spec.rules}

    def run(self) -> list[SpecIssue]:
        self._check_entities()
        self._check_relationships()
        self._check_operations()
        self._check_auth_and_policies()
        self._check_rules()
        self._check_seed()
        self._check_bindings()
        self._check_unsupported()
        return self.issues

    def _add(self, code: SpecIssueCode, path: str, message: str, hint: str | None = None, warning: bool = False):
        severity = Severity.WARNING if warning else Severity.ERROR
        self.issues.append(SpecIssue(code=code, path=path, message=message, hint=hint, severity=severity))

    def _entity_ref(self, name: str | None, path: str) -> Entity | None:
        if name is None:
            return None
        entity = self.entities.get(name)
        if entity is None:
            self._add(C.UNKNOWN_ENTITY_REF, path, f"Unknown entity '{name}'", hint=self._known_entities())
        return entity

    def _field_refs(self, entity: Entity | None, names: Iterable[str], path: str) -> None:
        if entity is None:
            return
        for index, name in enumerate(names):
            if name.lstrip("-") not in self.fields[entity.name]:
                self._add(C.UNKNOWN_FIELD_REF, f"{path}/{index}", f"Entity '{entity.name}' has no field '{name}'")

    def _known_entities(self) -> str:
        return f"Known entities: {', '.join(self.entities) or '(none)'}"

    def _check_entities(self) -> None:
        seen_names: dict[str, int] = {}
        seen_tables: dict[str, int] = {}
        for e_index, entity in enumerate(self.spec.entities):
            path = f"/entities/{e_index}"
            keys = ((entity.name.lower(), seen_names, "name"), (self._table(entity), seen_tables, "table"))
            for key, registry, what in keys:
                if key in registry:
                    message = f"Entity {what} '{key}' duplicates /entities/{registry[key]}"
                    self._add(C.DUPLICATE_ENTITY, f"{path}/name", message)
                registry.setdefault(key, e_index)

            primaries = [field for field in entity.fields if field.primary]
            if not primaries:
                self._add(C.PRIMARY_KEY_MISSING, f"{path}/fields", f"Entity '{entity.name}' has no primary key field")
            elif len(primaries) > 1:
                self._add(
                    C.PRIMARY_KEY_MULTIPLE, f"{path}/fields", f"Entity '{entity.name}' has more than one primary key"
                )

            columns: dict[str, int] = {}
            for f_index, field in enumerate(entity.fields):
                f_path = f"{path}/fields/{f_index}"
                column = to_snake(field.name)
                if column in columns:
                    self._add(
                        C.DUPLICATE_FIELD,
                        f"{f_path}/name",
                        f"Field '{field.name}' collides with field #{columns[column]} (column '{column}')",
                    )
                columns.setdefault(column, f_index)
                if field.type == "enum" and not field.values:
                    self._add(C.ENUM_VALUES_MISSING, f"{f_path}/values", f"Enum field '{field.name}' needs 'values'")
                if field.default is not None and not value_matches_type(field.default, field):
                    self._add(
                        C.TYPE_DEFAULT_MISMATCH,
                        f"{f_path}/default",
                        f"Default {field.default!r} is not a valid {field.type} for '{field.name}'",
                    )

            for i_index, index in enumerate(entity.indexes):
                self._field_refs(entity, index.fields, f"{path}/indexes/{i_index}/fields")
            for u_index, constraint in enumerate(entity.unique_constraints):
                self._field_refs(entity, constraint, f"{path}/uniqueConstraints/{u_index}")

    def _table(self, entity: Entity) -> str:
        return entity.table or table_name(entity.name)

    def _primary(self, entity: Entity) -> FieldDef | None:
        return next((field for field in entity.fields if field.primary), None)

    def _check_relationships(self) -> None:
        seen: dict[str, int] = {}
        for r_index, rel in enumerate(self.spec.relationships):
            path = f"/relationships/{r_index}"
            if rel.name.lower() in seen:
                self._add(C.DUPLICATE_RELATIONSHIP, f"{path}/name", f"Relationship '{rel.name}' is defined twice")
            seen.setdefault(rel.name.lower(), r_index)

            parent = self._entity_ref(rel.from_, f"{path}/from")
            child = self._entity_ref(rel.to, f"{path}/to")

            if rel.through is not None:
                if rel.type != "many-to-many":
                    self._add(
                        C.MANY_TO_MANY_THROUGH_INVALID, f"{path}/through", "'through' is only valid for many-to-many"
                    )
                elif rel.through in (rel.from_, rel.to):
                    self._add(
                        C.MANY_TO_MANY_THROUGH_INVALID, f"{path}/through", "Join entity must differ from both sides"
                    )
                else:
                    self._entity_ref(rel.through, f"{path}/through")

            if rel.type == "many-to-many":
                if rel.foreign_key is not None:
                    self._add(C.SCHEMA_VIOLATION, f"{path}/foreignKey", "many-to-many uses 'through', not 'foreignKey'")
                continue
            if parent is None or child is None:
                continue
            fk_name = rel.foreign_key or default_foreign_key(parent.name)
            fk_field = self.fields[child.name].get(fk_name)
            if fk_field is None:
                if rel.foreign_key is not None:
                    self._add(
                        C.UNKNOWN_FIELD_REF, f"{path}/foreignKey", f"Entity '{child.name}' has no field '{fk_name}'"
                    )
                continue
            parent_pk = self._primary(parent)
            if parent_pk and fk_field.type != parent_pk.type:
                self._add(
                    C.FOREIGN_KEY_TYPE_MISMATCH,
                    f"{path}/foreignKey",
                    f"'{child.name}.{fk_name}' is {fk_field.type} but '{parent.name}' primary key is {parent_pk.type}",
                )

    def _check_operations(self) -> None:
        ids: dict[str, int] = {}
        routes: dict[tuple[str, str], int] = {}
        for o_index, op in enumerate(self.spec.operations):
            path = f"/operations/{o_index}"
            if op.operation_id in ids:
                self._add(
                    C.DUPLICATE_OPERATION_ID,
                    f"{path}/operationId",
                    f"operationId '{op.operation_id}' duplicates /operations/{ids[op.operation_id]}",
                )
            ids.setdefault(op.operation_id, o_index)

            route = (op.method, _norm_route(op.path))
            if route in routes:
                self._add(
                    C.ROUTE_CONFLICT,
                    f"{path}/path",
                    f"{op.method} {op.path} conflicts with /operations/{routes[route]}",
                    hint="Paths that differ only in parameter names are the same route",
                )
            routes.setdefault(route, o_index)

            entity = self._entity_ref(op.entity, f"{path}/entity")
            if op.type == "crud":
                self._check_crud(op, entity, path)
            for key in ("filters", "sort", "search"):
                self._field_refs(entity, getattr(op, key), f"{path}/{key}")
            for key in ("request", "response"):
                self._check_payload(getattr(op, key), f"{path}/{key}")
            for r_index, rule_id in enumerate(op.rules):
                if rule_id not in self.rule_ids:
                    self._add(C.UNKNOWN_RULE_REF, f"{path}/rules/{r_index}", f"Unknown rule '{rule_id}'")

    def _check_crud(self, op: Operation, entity: Entity | None, path: str) -> None:
        if op.action is None:
            self._add(C.SCHEMA_VIOLATION, f"{path}/action", "crud operations require 'action'")
            return
        if op.entity is None:
            self._add(C.SCHEMA_VIOLATION, f"{path}/entity", "crud operations require 'entity'")
        if op.method not in _ACTION_METHODS[op.action]:
            expected = " or ".join(sorted(_ACTION_METHODS[op.action]))
            self._add(C.METHOD_ACTION_MISMATCH, f"{path}/method", f"'{op.action}' must use {expected}, not {op.method}")

        params = _PATH_PARAM.findall(op.path)
        if len(params) != len(set(params)):
            self._add(C.PATH_PARAM_MISMATCH, f"{path}/path", "Path parameters must be unique")
        if op.action in _ITEM_ACTIONS:
            if not op.path.rstrip("/").endswith("}"):
                self._add(
                    C.PATH_PARAM_MISMATCH,
                    f"{path}/path",
                    f"'{op.action}' needs the record id as the last path segment, e.g. {op.path.rstrip('/')}/{{id}}",
                )
            params = params[:-1]
        if entity is not None:
            for param in params:
                if param not in self.fields[entity.name]:
                    self._add(
                        C.PATH_PARAM_MISMATCH,
                        f"{path}/path",
                        f"Path parameter '{param}' is not a field of '{entity.name}'",
                    )

    def _check_payload(self, payload, path: str) -> None:
        if payload is None:
            return
        entity = self._entity_ref(payload.entity, f"{path}/entity")
        if payload.fields is not None:
            if payload.entity is None:
                self._add(C.SCHEMA_VIOLATION, f"{path}/fields", "'fields' requires 'entity'")
            self._field_refs(entity, payload.fields, f"{path}/fields")
        if payload.entity is None and not payload.properties:
            self._add(C.SCHEMA_VIOLATION, path, "Payload needs 'entity' or 'properties'")

    def _check_auth_and_policies(self) -> None:
        auth = self.spec.auth
        if auth is not None:
            user_entity = self.entities.get(auth.user_entity)
            if user_entity is not None and auth.login_field not in self.fields[user_entity.name]:
                self._add(
                    C.UNKNOWN_FIELD_REF,
                    "/auth/loginField",
                    f"Entity '{auth.user_entity}' has no field '{auth.login_field}'",
                )
        for p_index, policy in enumerate(self.spec.policies):
            if policy.type == "role" and not policy.roles:
                self._add(C.SCHEMA_VIOLATION, f"/policies/{p_index}/roles", "Role policies need at least one role")
            if policy.type == "ownership" and not policy.owner_field:
                self._add(C.SCHEMA_VIOLATION, f"/policies/{p_index}/ownerField", "Ownership policies need 'ownerField'")
            if auth is not None and auth.roles:
                for r_index, role in enumerate(policy.roles):
                    if role not in auth.roles:
                        self._add(
                            C.UNKNOWN_ROLE_REF,
                            f"/policies/{p_index}/roles/{r_index}",
                            f"Role '{role}' is not declared in auth.roles",
                        )

        for o_index, op in enumerate(self.spec.operations):
            path = f"/operations/{o_index}"
            if (op.auth == "jwt" or op.policy) and auth is None:
                self._add(
                    C.AUTH_NOT_CONFIGURED,
                    f"{path}/{'auth' if op.auth == 'jwt' else 'policy'}",
                    f"'{op.operation_id}' requires authentication but the spec has no top-level 'auth'",
                )
            if op.policy is None:
                continue
            policy = self.policies.get(op.policy)
            if policy is None:
                self._add(C.UNKNOWN_POLICY_REF, f"{path}/policy", f"Unknown policy '{op.policy}'")
            elif policy.type == "ownership" and policy.owner_field and op.entity in self.fields:
                if policy.owner_field not in self.fields[op.entity]:
                    self._add(
                        C.UNKNOWN_FIELD_REF,
                        f"{path}/policy",
                        f"Policy '{policy.name}' uses ownerField '{policy.owner_field}', missing on '{op.entity}'",
                    )

    def _check_rules(self) -> None:
        seen: dict[str, int] = {}
        for r_index, rule in enumerate(self.spec.rules):
            path = f"/rules/{r_index}"
            if rule.id in seen:
                self._add(C.DUPLICATE_RULE_ID, f"{path}/id", f"Rule id '{rule.id}' duplicates /rules/{seen[rule.id]}")
            seen.setdefault(rule.id, r_index)
            entity = self._entity_ref(rule.entity, f"{path}/entity")
            if entity is None:
                continue
            fields = self.fields[entity.name]
            params = rule.params

            if rule.kind == "custom":
                if not rule.description:
                    self._add(C.RULE_PARAMS_INVALID, f"{path}/description", "Custom rules need a 'description'")
                continue
            if rule.kind == "ownerOnly":
                if self.spec.auth is None:
                    self._add(C.AUTH_NOT_CONFIGURED, f"{path}/kind", "ownerOnly rules need top-level 'auth'")
                if params.get("ownerField") not in fields:
                    self._add(
                        C.UNKNOWN_FIELD_REF, f"{path}/params/ownerField", "ownerOnly needs an existing 'ownerField'"
                    )
                continue

            field = fields.get(params.get("field")) if isinstance(params.get("field"), str) else None
            if field is None:
                self._add(C.UNKNOWN_FIELD_REF, f"{path}/params/field", f"'{rule.kind}' needs an existing 'field'")
                continue
            if rule.kind == "transition":
                self._check_transition(field, params.get("transitions"), path)
            elif rule.kind == "immutableAfter":
                states = params.get("states")
                if field.type != "enum" or not isinstance(states, list) or not set(states) <= set(field.values or []):
                    self._add(
                        C.RULE_PARAMS_INVALID,
                        f"{path}/params/states",
                        "'immutableAfter' needs an enum 'field' and 'states' drawn from its values",
                    )
            elif rule.kind == "sumEquals" and field.type not in ("integer", "float", "decimal"):
                self._add(C.RULE_PARAMS_INVALID, f"{path}/params/field", "'sumEquals' needs a numeric 'field'")

    def _check_transition(self, field: FieldDef, transitions: Any, path: str) -> None:
        values = set(field.values or [])
        valid = (
            field.type == "enum"
            and isinstance(transitions, dict)
            and all(
                source in values and isinstance(targets, list) and set(targets) <= values
                for source, targets in transitions.items()
            )
        )
        if not valid:
            self._add(
                C.RULE_PARAMS_INVALID,
                f"{path}/params/transitions",
                "'transition' needs an enum 'field' and 'transitions' mapping each state to allowed next states",
                hint=f"States: {', '.join(sorted(values))}" if values else None,
            )

    def _check_seed(self) -> None:
        for s_index, seed in enumerate(self.spec.seed):
            path = f"/seed/{s_index}"
            entity = self._entity_ref(seed.entity, f"{path}/entity")
            if entity is None:
                continue
            fields = self.fields[entity.name]
            primary = self._primary(entity)
            seen_keys: set[str] = set()
            for row_index, record in enumerate(seed.records):
                row_path = f"{path}/records/{row_index}"
                for key, value in record.items():
                    field = fields.get(key)
                    if field is None:
                        self._add(C.SEED_INVALID, f"{row_path}/{key}", f"'{entity.name}' has no field '{key}'")
                    elif value is None:
                        if field.required or field.primary:
                            self._add(C.SEED_INVALID, f"{row_path}/{key}", f"'{key}' is required")
                    elif not value_matches_type(value, field):
                        self._add(C.SEED_INVALID, f"{row_path}/{key}", f"{value!r} is not a valid {field.type}")
                for name, field in fields.items():
                    auto_key = field.primary and field.type in ("uuid", "integer")
                    needed = (field.required or field.primary) and field.default is None and not auto_key
                    if needed and name not in record:
                        self._add(C.SEED_INVALID, row_path, f"Missing required field '{name}'")
                if primary is not None and primary.name in record:
                    key = json.dumps(record[primary.name])
                    if key in seen_keys:
                        self._add(C.SEED_INVALID, f"{row_path}/{primary.name}", f"Duplicate primary key {key}")
                    seen_keys.add(key)

    def _check_bindings(self) -> None:
        operation_ids = {op.operation_id for op in self.spec.operations}
        for b_index, binding in enumerate(self.spec.frontend_bindings):
            if binding.operation_id not in operation_ids:
                self._add(
                    C.UNKNOWN_OPERATION_REF,
                    f"/x-frontendBindings/{b_index}/operationId",
                    f"Binding refers to unknown operation '{binding.operation_id}'",
                )

    def _check_unsupported(self) -> None:
        for key, items in (("integrations", self.spec.integrations), ("backgroundJobs", self.spec.background_jobs)):
            for index, item in enumerate(items):
                self._add(
                    C.UNSUPPORTED_FEATURE,
                    f"/{key}/{index}",
                    f"'{item.name}' will be generated as a stub and listed as unresolved",
                    warning=True,
                )
