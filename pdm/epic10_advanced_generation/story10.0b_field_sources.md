# Story 10.0b — The integration contract: field sources, parent summaries, allowed actions, errors, scenarios

**Epic:** [10 — Advanced generation](epic10_advanced_generation.md) · **Requirements:** FR-35, FR-23 · **Depends on:** —

Re-scoped 2026-11-05: the contract and backend half stays here (backend first); the pickers, hidden fields and labels
in the generated frontend moved to [22.6](../epic22_dynamic_app_frontend/story22.6_reference_pickers.md).

## User story

As a frontend (generated or hand-written) using a generated API, I can tell from the contract where every request
value comes from, read related records by name, know what I may do with each record, show every rejection
properly, and prove that mocks and the live backend behave the same, without implementing a single business rule
myself.

**Principle (agreed 2026-11-05):** the backend decides; a frontend only reads what the contract and the responses say.
Each rule has one definition in the plan, and codegen writes from it the backend code, the mock behaviour and the
scenarios that check both.

## Problem

The contract says what an operation accepts, not where each value comes from. A card's `deckId` reaches the frontend
as a `string` field, so the user is asked for a UUID. The facts needed to do better are all in the plan already:
foreign keys (`column.foreignKey`), the detail routes, and (with 10.2 and 10.3) the owner field.

## Steps

1. **`x-bga.source` on every request property** in the contract (`orchestrator/integration/contract.py`), written by
   the planner:

   | Source | When |
   |---|---|
   | `server` | `id`, timestamps, computed fields |
   | `currentUser` | owner field (10.3) |
   | `route` | a foreign key whose parent has a detail route (`/decks/{id}` → `deckId`), so a frontend may take it from there |
   | `reference` | a foreign key (also when `route` applies): `x-bga.ref: {entity, listOperation, labelField}` |
   | `upload` | `file` / `image` field (10.5) |
   | `input` | everything else |

2. **Label field:** `entities[].displayField` (new, additive), else the first of `name`, `title`, `label`, `email`,
   else the first required string field. The drafter sets `displayField` when it is not obvious.
3. **Parent summaries in responses:** a child's response DTO gains a summary of each parent (`deck: {id, name}`)
   through the response-fields path of codegen; the repository loads parents in one query per page, not per row.
   Mocks and fixtures carry the same summaries.
4. **A list operation per referenced parent:** the planner adds the parent's `list` when a reference needs one and the
   BackendSpec has none (noted).
5. **Conflict fields:** codegen's unique-field 409s carry `details: {"fields": [...]}` (the unique columns), and 422s
   keep FastAPI's `loc`, so a frontend can show the error on the field (used by 22.5).
6. **`FE_FIELD_SOURCE`** in the pair check (`checks/consistency.py`): every required request field of every bound form
   has a source that works on its page (a `route` source needs that route parameter; a `reference` needs the parent's
   list operation). `pair_fixes` repairs what it can (hide a field the route provides, turn a foreign key into a
   reference, add the parent's list operation to the BackendSpec); what is left fails the draft with a clear note. It
   runs on today's dynamic drafts and on app drafts (22.3).
7. **Allowed actions per record:** every entity response with record operations carries `allowedActions: string[]`
   (`update`, `delete`, each custom record operation id, and later `transition:<STATE>`, `pay`, `create:<child>`),
   computed on the backend through the response-fields path. Here every action is allowed; plugins narrow it (10.3
   ownership and roles, 10.4 transitions and locks, 10.9 pay, 10.10 capacity). MSW computes the same list from the
   same plan entries.
8. **Errors per operation:** `x-bga.errors` lists what each operation can answer besides success:
   `{status, code, fields, message}` (422 validation, 404 unknown id, 409 unique fields, and later each rule's code,
   10.3–10.10). A `custom` rule gets an error code and its field from the planner, so the engine raises a known code
   and the frontend has a message for it.
9. **Scenarios:** `x-bga.scenarios` per operation, written by code from the fixtures and the errors above: the
   success call, an unknown id (404), a missing required field (422), a duplicate unique value (409), each with the
   expected status, code and response shape. Plugins add theirs (another user's record, an illegal transition, a full
   workshop). Validation's smoke check (18.11) runs them against the backend; Epic 22 runs the same scenarios against
   MSW and, after the switch to live, through the frontend's API path.

## Acceptance criteria

- [ ] Every request property in the contract of every example has an `x-bga.source`; foreign keys carry `x-bga.ref`.
- [ ] Child responses carry parent summaries, loaded in one query per page (a test counts the queries); mocks and
      fixtures match.
- [ ] Unique-field 409s carry `details.fields`; template tests check them.
- [ ] A draft whose form needs a value it cannot get is repaired or rejected by `FE_FIELD_SOURCE`, with a test for
      each repair.
- [ ] Every entity response carries `allowedActions`; mocks return the same list for the same record.
- [ ] Every operation lists its errors in `x-bga.errors`; a `custom` rule has a code and a field.
- [ ] Scenarios are generated for every operation of the examples and pass against the backend in validation (smoke
      check); a planted mismatch (wrong status or code) fails it.
- [ ] Contract snapshots updated (`UPDATE_SNAPSHOTS=1`); OpenAPI conformance still passes.

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test` at the checkpoint's end; `make up`, generate
`flashcards-dynamic` with the fake engine and check a card's response and the contract in the try-it explorer.

## Status

**Planned (2026-11-04)**, re-scoped to the contract and backend on 2026-11-05.
