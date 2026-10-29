# Story 17.6 — Backend CRUD from templates

**Epic:** [17 — Fast generation](epic17_fast_generation.md) · **Requirements:** FR-30, FR-04, FR-05 · **Depends on:** 5.3, 12.3

## User story

As a user, I want the routine parts of my backend (models, repositories, CRUD endpoints, migrations, tests)
written instantly from the spec, and the code engine used only for the parts that are specific to my app.

## Acceptance criteria

- [ ] For every BackendSpec entity, codegen writes the fastapi-skills module deterministically: SQLModel model,
      entity, output port, repository + `I<Name>RepoDep`, use cases + `Dep` aliases, DTOs, router, registration
      in `routers.py` and `modules/__init__.py`, an Alembic migration, seed hook and CRUD tests.
- [ ] Output is byte-identical between runs and snapshot-tested like the contract; generated files are
      overlay-owned (checked by `conventions`).
- [ ] The engine is called only for what is not CRUD (custom operations, business rules, non-trivial
      validation), with the generated modules as context and edits limited to the files of that feature.
- [ ] A CRUD-only spec (`two-entity`) makes no engine call for its modules and passes the existing validation
      (syntax, lint, deps, startup, migration, conventions, tests, openapi); the OpenAPI still matches the
      contract in dynamic mode.
- [ ] The integration wait (`INTEGRATION_WAIT_SECONDS`, 14.2) no longer cancels a backend that is still being
      written: since 17.3 the frontend lane can finish in ~10 min, and the 900 s wait that starts then cancelled a
      4-module Antigravity backend mid-generation (`gen_01M63AKY87M697K7P9A7VGK2ET`). Start the wait when the
      backend reaches validation (or otherwise bound it by backend progress), with a test.
- [ ] Status note records backend-lane time before and after, and whether caching custom operations (like
      17.3) is worth a follow-up story.

**Status:** open.
