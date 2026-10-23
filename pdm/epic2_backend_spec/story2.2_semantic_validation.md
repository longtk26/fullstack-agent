# Story 2.2 — Semantic spec validation

**Epic:** [2 — BackendSpec](epic2_backend_spec.md) · **Requirements:** FR-01, FR-02 · **Depends on:** 2.1

## User story

As a spec author, I want every structural and referential problem reported in one pass, with precise
locations, so that I can fix the spec before spending any generation time.

## Acceptance criteria

- [x] Deterministic validator returns `ValidationReport{valid, errors[], warnings[]}`. Each issue is
      `{code, path (JSON pointer), message, hint?}`.
- [x] Rules and codes:

| Code | Rule |
|---|---|
| `JSON_MALFORMED` | body is not parseable JSON |
| `SCHEMA_VIOLATION` | Pydantic or JSON Schema failure (missing required field, wrong type, unsupported value) |
| `DUPLICATE_ENTITY` / `DUPLICATE_FIELD` / `DUPLICATE_OPERATION_ID` | name collisions (case-insensitive; fields compared by column name, so `createdAt` ≡ `created_at`) |
| `DUPLICATE_RELATIONSHIP` / `DUPLICATE_RULE_ID` | relationship name or rule id reused |
| `ROUTE_CONFLICT` | same method + normalized path (`/tasks/{id}` ≡ `/tasks/{taskId}`) |
| `PRIMARY_KEY_MISSING` / `PRIMARY_KEY_MULTIPLE` | each entity needs exactly one PK (MVP) |
| `UNKNOWN_ENTITY_REF` | operation, relationship or rule references a missing entity |
| `UNKNOWN_FIELD_REF` | index, constraint, filter, sort, search, payload field, foreignKey, loginField, rule field or ownerField references a missing field |
| `UNKNOWN_OPERATION_REF` / `UNKNOWN_RULE_REF` | frontend binding or operation `rules[]` references a missing operation / rule |
| `TYPE_DEFAULT_MISMATCH` | default not compatible with field type, range, length or enum values (`"now"` allowed for date/datetime) |
| `FOREIGN_KEY_TYPE_MISMATCH` | FK field type differs from the parent's primary key type |
| `ENUM_VALUES_MISSING` | `type: enum` without `values` |
| `AUTH_NOT_CONFIGURED` | operation has `auth`/`policy` but no top-level `auth` |
| `UNKNOWN_POLICY_REF` / `UNKNOWN_ROLE_REF` | policy or role not defined |
| `PATH_PARAM_MISMATCH` | path params do not match the action (e.g. `get` without `{id}` last), duplicate params, or a non-id param that is not an entity field |
| `METHOD_ACTION_MISMATCH` | crud action used with the wrong HTTP method (create→POST, get/list→GET, update→PUT/PATCH, delete→DELETE) |
| `RULE_PARAMS_INVALID` | rule params inconsistent with its kind (e.g. transition to a state not in the enum) |
| `MANY_TO_MANY_THROUGH_INVALID` | invalid join entity |
| `SEED_INVALID` | seed entity unknown, record key not a field, value incompatible with the field type, or duplicate PK |
| `UNSUPPORTED_FEATURE` (warning) | integrations, backgroundJobs, or anything recorded as unresolved |

- [x] The validator collects all errors and does not stop at the first one.
- [x] Normalization fills defaults (e.g. `required: false`, table name = snake_case plural) into `normalized_json`.
- [x] Each rule has a fixture under `tests/fixtures/specs/invalid/` asserting its code and path.
