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
   | `server` | `id`, timestamps, computed fields (not in the request at all) |
   | `currentUser` | owner field (10.3) |
   | `reference` | a foreign key: `x-bga.ref: {entity, listOperation, detailOperation, labelField}`; a page that shows the parent (its detail bound to a route parameter) takes it from the route |
   | `upload` | `file` / `image` field (10.5) |
   | `input` | everything else |

2. **Label field:** `entities[].displayField` (new, additive), else the first of `name`, `title`, `label`, `email`,
   else the first required string field. The drafter sets `displayField` when it is not obvious.
3. **Parent summaries in responses:** a child's response DTO gains a summary of each parent (`deck: {id, label}`)
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

- [x] Every request property in the contract of every example has an `x-bga.source`; foreign keys carry `x-bga.ref`.
- [x] Child responses carry parent summaries, loaded in one query per page (a test counts the queries); mocks and
      fixtures match.
- [x] Unique-field 409s carry `details.fields`; template tests check them.
- [x] A draft whose form needs a value it cannot get is repaired or flagged by `FE_FIELD_SOURCE`, with a test for
      each repair. *(Flagged as a warning, not rejected: see Status.)*
- [x] Every entity response carries `allowedActions`; mocks return the same list for the same record.
- [x] Every operation lists its errors in `x-bga.errors`. *(A `custom` rule's code and field: moved to 10.4.)*
- [x] Scenarios are generated for every operation of the examples and pass against the backend in validation (smoke
      check); a planted mismatch (wrong status or code) fails it.
- [x] Contract snapshots updated (`UPDATE_SNAPSHOTS=1`); OpenAPI conformance still passes.

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test` at the checkpoint's end; `make up`, generate
`flashcards-dynamic` with the fake engine and check a card's response and the contract in the try-it explorer.

## Status

**Done (2026-11-05)** on `feat/epic10-backend-plugins`, under the user's review.

- **Planner** (`backend/planner.py`): each model gets a `label` (`displayField`, else `name` / `title` / `label` /
  `email`, else the first required string) and `references` (each foreign key to a labelled parent, shown as
  `deckId` → `deck`; a Python keyword gets `_` and an alias); each module gets `recordActions` (update, delete, and
  custom writes whose path parameter is the record's id, e.g. `card.review`); modules with references get a
  `references` port method. BackendSpec `entities[].displayField` is new (additive) and validated.
- **Contract** (`integration/contract.py`): `x-bga.source` and `x-bga.ref` on request properties; `{Entity}Summary`
  schemas; record responses with a nullable summary per reference and `allowedActions` (an enum of the module's
  record actions); `x-bga.errors` per operation (status, code, message, fields); `x-bga.scenarios` per CRUD
  operation; `x-bga.entities` for the mocks; response examples presented like the API answers.
  `presented_record(contract, entity, row)` gives the same from the contract alone.
- **Backend codegen** (`backend/codegen.py`): `src/modules/shared/presenter/summaries.py` (one `{id, label}` DTO per
  parent, `References`); response DTOs with `ALLOWED_ACTIONS`, summaries and `from_entity(entity, references=None)`;
  repositories' `references(records)`, one `IN` query per reference for a whole page; use cases pass them; unique
  409s carry `details.fields`, reference 400s too; the conflict template test checks the fields. The
  `complete_backend` context pack tells the engine how to return records with their references.
- **Mocks** (dynamic overlay only): `handlers.ts` presents every record from `src/mocks/entities.json`; the TS types
  map nullable references (`deck: TDeckSummary | null`).
- **Smoke check** (`checks/smoke.py`): the scenarios run before the custom operations, each needing its exact status
  and error code; the summary counts both.
- **Pair check**: `FE_FIELD_SOURCE` flags a visible field for a reference (the form asks for an id); the pair fixes
  hide it and take `$route.<p>` when every page showing the form already shows the parent.
- **Golden engine path** (fake engine only): the two-entity and shop golden modules, and the flashcards custom use
  cases, return the new fields; the golden OpenAPI export was regenerated from that project.

**Deviations:**

- `FE_FIELD_SOURCE` is a **warning**, not an error: a form not on the parent's page has no way to pick the parent
  until 22.6's picker, and rejecting every such draft would block drafting until Epic 22. `flashcards-dynamic`'s
  `new_card_form` (on `/cards/new`) is flagged.
- The planner does not add a missing list operation for a referenced parent (step 4): `x-bga.ref.listOperation` is
  `null` then, and adding the list belongs with the picker that needs it (22.6).
- A `custom` rule's error code and field moved to 10.4 (the rules plugin and its engine note).
- No `route` source: a foreign key is always `reference`, and the route is a page's choice (22.3), with
  `x-bga.ref.detailOperation` to find it.
- Summaries are `{id, label}`, not `{id, name}`, so every parent reads the same way.
- The two-entity engine export (`tests/fixtures/openapi/two-entity.engine.json`, a real engine run from Epic 12) was
  not regenerated (that needs a paid run); its test now proves conformance names exactly what it lacks.
- Smoke calls now run for every backend with CRUD operations, not only those with custom operations (a few seconds:
  seeding and one uvicorn start).

**Verified:** `make lint`; `tests/test_integration_contract.py` (14 tests); the codegen, contract, planner, validator,
consistency, pair-fix, frontend, parallel-generation, lean-validation and completion tests; `UPDATE_SNAPSHOTS=1` for
the codegen, contract and plan snapshots; `BGA_SANDBOX_TESTS=1` for `tests/sandbox/test_sandbox_workflow.py` (real
sandbox: the flashcards backend answers every scenario and custom call; template tests check the conflict fields).
`make test`: all pass. `make up`, then a fake-engine `flashcards-dynamic` generation
(`gen_01M6MSHJYENZPVWAH0N9KG1V0G`): COMPLETED in 96 s, all three lanes completed; validation's tests check: 38 template
tests passed, "3 custom operation(s), 21 scenario(s) answer as the contract says"; the live preview answers
`GET /cards` with `deck: {id, label: "Spanish Basics"}` and `allowedActions: ["update", "delete", "card.review"]`; the
frontend has `src/mocks/entities.json`.
