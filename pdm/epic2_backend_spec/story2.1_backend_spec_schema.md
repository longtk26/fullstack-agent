# Story 2.1 — BackendSpec v1.0 schema & JSON Schema export

**Epic:** [2 — BackendSpec](epic2_backend_spec.md) · **Requirements:** FR-01, NFR 8.4

## User story

As a spec author (human or upstream agent), I want a published, versioned schema so that I know exactly
what input is accepted and my editor can autocomplete it.

## Acceptance criteria

- [x] Pydantic v2 models (`extra="forbid"`, camelCase aliases) for `specVersion: "1.0"`:
  - `project` {name, description?, slug (derived)}
  - `stack` {framework: `fastapi`, database: `postgresql`, orm: `sqlalchemy|sqlmodel`, migration: `alembic`}. Literal enums only.
  - `entities[]` {name (PascalCase), table?, description?, fields[], indexes[], uniqueConstraints[]}. Ownership is expressed by `policies[].ownerField`.
  - `fields[]` {name, type: `uuid|string|text|integer|float|decimal|boolean|date|datetime|enum|json`,
    primary?, required?, nullable?, unique?, index?, default?, values? (enum), maxLength?, min?, max?}
  - `relationships[]` {name, type: `one-to-one|one-to-many|many-to-many`, from, to, foreignKey? (defaults to `<from>Id` on `to`), onDelete?, through?}
  - `operations[]` {operationId (stable, `^[a-z][a-zA-Z0-9]*(\.[a-zA-Z0-9]+)+$`), type: `crud|custom`,
    action (`create|get|list|update|delete` for crud), entity, method, path, summary?, auth?, policy?,
    request?, response? ({entity, fields?} or {properties[]}), pagination? (bool or {defaultLimit, maxLimit}), filters[]?, sort[]?, search[]?, rules[]?}
  - `auth` {type: `jwt`, userEntity, loginField, roles[]} (optional)
  - `policies[]` {name, type: `role|ownership`, roles?, ownerField?}
  - `rules[]` {id, kind: `transition|immutableAfter|ownerOnly|sumEquals|custom`, entity, params, description}
  - `integrations[]`, `backgroundJobs[]`: accepted and stored, but marked unsupported in MVP (see 10.4)
  - `seed[]` {entity, records[]} (optional, added for 2.5): rows loaded into the **preview** DB only (7.3),
    never into migrations. Record keys must match entity fields.
  - Primary keys may be `uuid` (default), `integer` or `string` (needed for imported ids like `art-01`).
- [x] `GET /api/v1/specs/schema?version=1.0` serves the JSON Schema produced by `model_json_schema()`.
      The same file is committed at `agent-api/schemas/backend-spec-1.0.json`.
- [x] Unknown `specVersion` → error `SPEC_VERSION_UNSUPPORTED`. A version registry makes adding `1.1` additive.
- [x] Unit tests: the §5 example parses. Each enum and type is covered.

## Technical notes

- Schema models live in `src/modules/shared/domain/backend_spec/` (shared because the planner, prompts and manifest also read them). They are pure Pydantic and import nothing from the framework.
- `make schema` (agent-api) regenerates the committed JSON Schema; a test fails if it drifts.
