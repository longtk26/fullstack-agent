# Story 5.5 — Test suite generation (`generate_tests`)

**Epic:** [5 — Backend generation](epic5_backend_generation.md) · **Requirements:** FR-07 (expected + rejected), FR-11 · **Depends on:** 5.4

## User story

As the workflow, I want a pytest suite derived from the plan's required test cases, so that validation proves
the API behaves, not just that it imports.

## Acceptance criteria

- [x] `tests/conftest.py` from the overlay: `DB_URL` pointed at the sandbox test DB, `alembic upgrade head` once
      per session, tables truncated per test, and `with TestClient(app)` so the lifespan runs and registers the routers.
- [x] The engine writes `tests/modules/<entities>/test_<entity>_api.py` covering every `plan.tests[]` case: happy path,
      404, 422 on invalid payload, pagination, filter, sort and search, and rules (expected + rejected) when present.
      Optional use-case unit tests use a fake repository that implements the port.
- [x] Deterministic coverage check: every planned test id appears as a test name (`test_<operation>__<case>`).
      Missing ones → validation error.
- [x] Skipped when `options.runTests=false`. The manifest then reports tests as `skipped`, not `passed`.
- [x] Commit `node:generate_tests`.

**Status (2026-10-23):** done. Planned test ids are `test_<handler>__<case>`; missing ones fail the `tests` check.
