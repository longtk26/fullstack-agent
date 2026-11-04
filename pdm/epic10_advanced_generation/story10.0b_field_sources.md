# Story 10.0b — Field sources and references

**Epic:** [10 — Advanced generation](epic10_advanced_generation.md) · **Requirements:** FR-35, FR-23 · **Depends on:** 10.0a

## User story

As a user of a generated app, I never type an ID: a form fills in what the server, the page or the signed-in user
already knows, and lets me pick a related record by its name.

## Problem

The contract says what an operation accepts, not where each value comes from. A card's `deckId` reaches the form
as a `string` field, so the user is asked for a UUID. The facts needed to do better are all in the plan already:
foreign keys (`column.foreignKey`), the page's route parameters and bindings, and (with 10.2 and 10.3) the owner
field.

## Steps

1. **`x-bga.source` on every request property** in the contract (`orchestrator/integration/contract.py`), written by the planner:

   | Source | When | Frontend |
   |---|---|---|
   | `server` | `id`, timestamps, computed fields | not in the form |
   | `currentUser` | owner field (10.3) | not in the form; the server sets it |
   | `route` | foreign key, and the form's page is under the parent's detail route (`/decks/[id]` → `deckId`) | hidden field, `$route.<param>` |
   | `reference` | foreign key with no route context | picker (below) |
   | `upload` | `file` / `image` field (10.5) | upload field |
   | `input` | everything else | the 10.0a component for its type |

   A `reference` property also carries `x-bga.ref: {entity, listOperation, labelField}`.
2. **Label field:** `entities[].displayField` (new, additive), else the first of `name`, `title`, `label`, `email`,
   else the first required string field. The drafter sets `displayField` when it is not obvious.
3. **Reference picker:** a Combobox (Popover + Command) that loads the parent's list operation, searching with `q`
   when the list has search, else the first 50 records filtered in the browser; shows the label, sends the id.
4. **Readable references in responses:** a child's response DTO gains a summary of each parent (`deck: {id, name}`)
   from the response-fields path of codegen (the repository loads parents in one query per page, not per row); list
   and detail sections show the label, never the id. Mocks and fixtures carry the same summaries.
5. **Binding completeness check** in the pair check (`checks/consistency.py`, code `FE_FIELD_SOURCE`): every required
   request field of every bound form must have a source that works on its page (a `route` source needs that route
   parameter; a `reference` needs the parent's list operation). `pair_fixes` repairs what it can (hide a field the
   route provides, turn a foreign key into a reference, add the parent's list operation to the BackendSpec); what is
   left fails the draft with a clear note.
6. **Manage area and journeys** (19.x) use the same sources.

## Acceptance criteria

- [ ] No generated form in the examples (`flashcards`, `project-tracker`, `shop`, `workshop-bookings`) shows an id
      input.
- [ ] A child created on its parent's page takes the parent from the route; elsewhere the parent is picked by its
      label.
- [ ] Lists and details show parents by label, on mocks and on the live backend.
- [ ] A draft whose form needs a value it cannot get is repaired or rejected by `FE_FIELD_SOURCE`, with a test for
      each repair.
- [ ] Contract snapshots updated (`UPDATE_SNAPSHOTS=1`); OpenAPI conformance still passes.

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test`; `make up`, generate `flashcards-dynamic` with the fake engine
and add a card from a deck's page and from the cards page.

## Status

**Planned (2026-11-04).**
