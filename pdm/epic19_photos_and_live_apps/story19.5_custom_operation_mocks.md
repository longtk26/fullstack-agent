# Story 19.5 — Custom operations on the mock API

**Epic:** [19 — Real photos and API-driven dynamic apps](epic19_photos_and_live_apps.md) · **Requirements:** FR-32 · **Depends on:** 13.2

## User story

As a user, I want the frontend to call my app's domain operations (review a card, list the due cards) even while it
runs on mocks, so that the screens built on them pass their checks before the backend is live.

## Context

- MSW handlers: `templates/nextjs_overlay/files/dynamic/src/mocks/handlers.ts` handles `list`, `get`, `create`,
  `update`, `delete` by `op.action`; anything else returns **501 NOT_IMPLEMENTED**.
- What each handler gets: `orchestrator/frontend_codegen.py` → `mock_operations(contract)` (operation id, method,
  path, entity, action, primary key, filters, sort, search, limits, fixtures).
- The contract: `orchestrator/contract.py` (`OpenApiBuilder.operation`, `build_fixtures`, `_synthesize`,
  `x-bga` metadata). Custom operations have `x-bga.action` = `None`.
- Mocks never compute domain logic (the scheduling of a review): the live journey tests (19.9) check that.

## Steps

1. **Mock plan per custom operation**, computed in `contract.py` and stored as `x-bga.mock` on the operation (so it
   is in the contract snapshot and reviewable):
   - `record`: GET, path has the entity's id, response is the entity → the fixture record with that id (404 if
     none);
   - `records`: GET, response is an array (or the list envelope) of the entity → the fixtures, filtered by query
     parameters whose names are entity fields (equality; `<field>Before` / `<field>After` style parameters compare
     dates if the spec uses them), paginated like `list`;
   - `merge`: POST / PUT / PATCH, path has the entity's id, response is the entity → merge the request body's
     fields that exist on the entity into the fixture record, keep it in the mock store, return it;
   - `create`: POST without an id, response is the entity → like `create`;
   - `sample`: anything else → a fixed, schema-valid sample of the response (built with `_synthesize` and the
     fixtures), status from the contract.
2. `mock_operations` passes `mock` through; `handlers.ts` handles each kind instead of answering 501. Keep 501 only
   for an operation with no mock plan (should not happen; log a warning in the handler).
3. Response status: the operation's first 2xx response, as today.
4. Tests:
   - Python: the mock plan for each case on a small spec (snapshot of the contract for the golden dynamic examples:
     `UPDATE_SNAPSHOTS=1`, review the diff);
   - sandbox (`BGA_SANDBOX_TESTS=1`): a vitest test in the golden dynamic site that calls each kind through MSW and
     checks the shape (find where the golden site's tests live: `docs/development/test-doubles.md`).

## Acceptance criteria

- [x] Every custom operation has a mock plan in the contract (`x-bga.mock`).
- [x] The mock API answers every operation of the contract; no 501 for custom operations.
- [x] `merge` changes persist in the mock store for the rest of the session.
- [x] Contract snapshots updated and reviewed; the sandbox test passes.

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test`, `make up` with the fake engine: dynamic
`project-tracker-dynamic` + `two-entity` still COMPLETED.
