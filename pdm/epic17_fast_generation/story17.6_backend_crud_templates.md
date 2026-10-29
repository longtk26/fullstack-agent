# Story 17.6 — Backend CRUD from templates

**Epic:** [17 — Fast generation](epic17_fast_generation.md) · **Requirements:** FR-30, FR-04, FR-05 · **Depends on:** 5.3, 12.3

## User story

As a user, I want the routine parts of my backend (models, repositories, CRUD endpoints, migrations, tests)
written instantly from the spec, and the code engine used only for the parts that are specific to my app.

## Acceptance criteria

- [x] For every BackendSpec entity, codegen writes the fastapi-skills module deterministically: SQLModel model,
      entity, output port, repository + `I<Name>RepoDep`, use cases + `Dep` aliases, DTOs, router, registration
      in `routers.py` and `modules/__init__.py`, an Alembic migration, seed hook and CRUD tests.
- [x] Output is byte-identical between runs and snapshot-tested like the contract; generated files are
      overlay-owned (checked by `conventions`).
- [x] The engine is called only for what is not CRUD (custom operations, business rules, non-trivial
      validation), with the generated modules as context and edits limited to the files of that feature.
- [x] A CRUD-only spec (`two-entity`) makes no engine call for its modules and passes the existing validation
      (syntax, lint, deps, startup, migration, conventions, tests, openapi); the OpenAPI still matches the
      contract in dynamic mode.
- [x] The integration wait (`INTEGRATION_WAIT_SECONDS`, 14.2) no longer cancels a backend that is still being
      written: since 17.3 the frontend lane can finish in ~10 min, and the 900 s wait that starts then cancelled a
      4-module Antigravity backend mid-generation (`gen_01M63AKY87M697K7P9A7VGK2ET`). Start the wait when the
      backend reaches validation (or otherwise bound it by backend progress), with a test.
- [x] Status note records backend-lane time before and after, and whether caching custom operations (like
      17.3) is worth a follow-up story.

**Status:** done (2026-10-29).

- `orchestrator/backend_codegen.py` writes, from the plan (and the spec's `request.fields`, through the contract's
  own `_request_columns` / `_required`): entities + enums, SQLModel models (FKs, `ondelete`, indexes, enums,
  `Numeric`, `Text`, tz-aware datetimes, JSONB, one-to-many relationships), the registrations, every CRUD module
  (port + Dep re-export, repository with filters / search / sort / pagination and `IntegrityError` mapping, use
  cases with `@Transactional` and `Dep`s, request / response / list DTOs, router with the planned operation ids,
  statuses and error responses), `src/routers.py`, and one API test per planned case (records inserted with the ORM,
  so entities without a create endpoint are tested too). The seed hook already existed (`seed.json` → preview).
- Output is a pure function of (spec, plan), snapshot-tested per example (`tests/fixtures/backend-codegen/`). The
  worker has no ruff, so `generate_database` / `generate_backend` / `generate_tests` format the files with the
  sandbox's ruff (as the scaffold step does for the template) and record them as owned (`scaffold.add_owned`).
- What the templates do not cover is named per module (`codegen_gaps`: custom operations, business rules, auth /
  policies) or for the models (`database_gaps`: one-to-one and many-to-many); only those go to the engine, with the
  new `complete_backend` prompt and the generated files as context. Modules the engine completes are not owned.
  `options.crudFromTemplates=false` restores the engine path; the tests of the engine, repair, cancel and resume
  plumbing use it.
- The integration wait now counts from when the backend reaches validation (`ctx.backend_validating`), so a backend
  still being written is never cancelled for being slower than the frontend; the job timeout bounds it.
- **Verified:** 452 tests without the Docker sandbox tests; in Docker, the generated `two-entity` and `shop` backends
  pass every check (syntax, lint, deps, startup, migration, conventions, the generated tests, OpenAPI conformance
  with the contract), and `task-management` did too in a manual run. A CRUD-only spec makes 0 backend engine calls.
- **Backend lane before / after:** with Antigravity the `shop` backend spent 5m14s in `generate_database` and ~10 min
  per module in `generate_backend` (4 modules), then test generation per module (`gen_01M63AKY87M697K7P9A7VGK2ET`,
  cancelled after 25 min). With the templates all of that is replaced by writing files (< 1 s) plus a ruff pass, so
  the lane is scaffold + migration + validation. Full stack, `shop-dynamic` + `shop` on Antigravity
  (`gen_01M63GCRJRPQC022SDWD1VYFT4`): **59 s end to end, 0 engine calls** (backend: models 18 s incl. the migration
  check, modules and tests < 1 s, validation 30 s; frontend rendered with the 3 cached components and validated in
  59 s). The integration was skipped only because the backend preview was not up yet when it ran.
- **Docker on this machine:** two Docker Desktop crashes and single-bit corruptions in built images point at faulty
  RAM (non-ECC); a memory test is advised before trusting further Docker results.
- **Caching custom operations** (like 17.3) is worth a follow-up only once specs with many custom operations exist;
  the examples have none.
