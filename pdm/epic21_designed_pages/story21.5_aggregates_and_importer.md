# Story 21.5 — Aggregates without the engine; the trees' operations in the BackendSpec

**Epic:** [21 — Designed pages](epic21_designed_pages.md) · **Depends on:** 17.6, 21.4

## User story

As a user, I want the figures and charts of a designed dashboard to come from the backend without an engine call,
and the records my pages show to have their operations, so that an app with a dashboard generates as fast as a CRUD
app and its backend matches its pages.

## Scope

- BackendSpec `type: "aggregate"` operations: `aggregate: {fn, field, groupBy, period, dateField, filters}`,
  checked by the validator (entity, numeric field, known group / date fields, GET).
- Templated like CRUD: the planner gives them a handler and a response DTO; `backend_codegen` writes the repository
  query (`select(func.sum(col(Model.field)))`, grouped, with the period and filters), the use case, the DTO, the
  router handler (declared above the `/{id}` routes) and a test; `codegen_gaps` no longer sends them to the engine.
- The contract describes `{value}` / `[{key, value}]` with `x-bga.action: "aggregate"`; the mock computes them from
  the fixtures (`handlers.ts`).
- `tree_bindings.derive_operations` + `tree_drafting.complete_backend_for_trees`: the CRUD and aggregate operations
  the trees' data components need, and entities (with seed) from collections the BackendSpec lacks, merged into a
  dynamic draft's BackendSpec; derived operations that do not validate are left out with a note.

## Acceptance criteria

- [x] A BackendSpec aggregate generates, validates and answers from templates (no `complete_backend` call).
- [x] The contract and the mock describe and serve aggregates; a tree's `Metric` / `Chart` binds to them.
- [x] A dynamic draft's trees add the operations and entities they need to its BackendSpec.

## Status

**Done (2026-11-04)**. Tests: `tests/test_aggregates.py` (validation, planning, generated files compile and contain
the queries, contract and mock entries, bindings, derived operations), `tests/test_tree_drafting.py`
(`complete_backend_for_trees`). Also fixed: `naming.singularize` turned "expenses" into "expens" (now "expense";
"classes" → "class", "statuses" → "status" still). Not done: a sandbox run of a generated aggregate (the template
tests cover the query text; the first real generation with a dashboard verifies it).
