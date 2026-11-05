# Story 10.10 — Capacity, no-overlap and unique-together rules

**Epic:** [10 — Advanced generation](epic10_advanced_generation.md) · **Requirements:** FR-07, FR-34 · **Depends on:** 10.4

## User story

As a spec author, I want the rules that break under concurrent requests (a full workshop, a double-booked room, a
second booking by the same user) generated from templates and enforced by the database, so that two requests at the
same moment cannot both succeed.

## Why

Today these go to the engine as custom rules, and a check-then-write in a use case lets two concurrent requests both
pass. They are common in booking, stock and scheduling apps, and each has a known correct shape.

## Acceptance criteria

- [x] New rule kinds in the `rules` plugin (BackendSpec `RuleKind`, additive):

| Kind | Example | Enforced by | Rejection |
|---|---|---|---|
| `capacity` | a workshop's active bookings ≤ `workshop.capacity` | use case locks the parent row (`SELECT … FOR UPDATE`) then counts, in one transaction | 409 `CAPACITY_REACHED` |
| `noOverlap` | a room's bookings never overlap in `[startsAt, endsAt)` | Postgres exclusion constraint (`btree_gist`, `tstzrange … &&`) in the migration; the violation is mapped | 409 `OVERLAP` |
| `uniqueTogether` | one booking per (user, workshop) | unique constraint across the fields; `IntegrityError` mapped with `details.fields` | 409 `DUPLICATE` |

- [x] Each kind takes a filter of which records count (e.g. `status != CANCELLED`), checked by the validator.
- [x] Template tests include **concurrent** requests (two sessions at once): exactly one succeeds.
- [ ] A full parent's `allowedActions` has no `create:<child>`; the 409s carry their code and `details.fields` in
      `x-bga.errors`; scenarios cover the last seat, a full workshop, an overlap and a duplicate; so the app can show
      "full" and the rejection on its field ([22.7](../epic22_dynamic_app_frontend/story22.7_plugin_frontends.md)).
- [x] The drafter maps "no double booking", "limited seats", "only once per user" to these kinds instead of
      `custom`.

## Status

**Done (2026-11-05)** on `feat/epic10-backend-plugins`, one criterion open (a full parent's `create:<child>`).

- **Spec**: `RuleKind` gains `capacity` (`{parent, capacityField, where?}` on the child entity), `noOverlap`
  (`{start, end, scope?, where?}`, date or datetime fields) and `uniqueTogether` (`{fields, where?}`); `where` takes
  `{field: value}` or `{field: {"ne"|"in"|"notIn": …}}`. The validator checks each (the parent is a foreign key, the
  capacity an integer of the parent, the range fields dates, enum values in `where`).
- **The rules plugin** (`orchestrator/plugins/concurrency.py`): they are data invariants, applied to the entity's
  writes whether or not an operation names them.
  - `capacity`: the create's pre-check calls a repository method that locks the parent row
    (`SELECT … FOR UPDATE`) and counts the children that count, in the request's transaction; 409
    `CAPACITY_REACHED` with the foreign key in `details.fields`.
  - `noOverlap`: an `ExcludeConstraint` (`tstzrange`/`daterange` with `&&`, `=` on the scope, `gist`, the `where` as
    its predicate) on the model; the overlay's Alembic `env.py` creates `btree_gist` when the metadata has an
    exclusion constraint. 409 `OVERLAP`.
  - `uniqueTogether`: a `UniqueConstraint`, or a partial unique `Index` with `where`; 409 `DUPLICATE`.
  - Constraint violations are mapped by name in the repository (`model.constraintErrors` → `CONSTRAINT_ERRORS`);
    models take plugin constraints through `model.tableArgs`. The three codes are in the overlay's `ErrorCode`.
- **Template tests**: per kind, two creates sent at once from two clients on the app: exactly one is 201, and the
  repeat answers the kind's code.
- **Contract**: the errors with their fields and rule; scenarios "<parent> full", "overlap" and "duplicate" from the
  fixtures (a noOverlap rule's fixtures get real ranges), and the success and the other create scenarios moved to
  records they do not collide with (a parent with room, a free slot, a pair of their own).
- **Drafting**: `draft_spec@v5` maps "no double booking", "limited seats", "only once per user" to these kinds.
- **Fixed on the way**: the schema check failed on an expression index (the exclusion constraint's GiST index
  reflects a column as None).

**Deviations:**

- A full parent's `allowedActions` has no `create:<child>` yet: the parent's response would need a count of its
  children per record; the contract's `CAPACITY_REACHED` and its scenario say when it is full. Follow-up.
- A capacity is checked on create only; an update that moves a record to another parent or back to a counting status
  is not checked (the constraints of the other two kinds hold on every write).

**Verified:** `make lint`; `tests/test_concurrency_rules.py` (4) and the rules and drafting tests; `make test` (all
pass after the schema digest update); `BGA_SANDBOX_TESTS=1` for the workshop-booking spec through the workflow
(`test_a_backend_with_concurrency_rules_passes_its_concurrent_tests_and_scenarios`): every check passes on the first
try after the scenario fixes (32 template tests with the three concurrent ones, 26 scenarios, the migration with the
exclusion constraint). `make up`, then a fake-engine backend generation of it (`gen_01M6NAP6N44C40HA1EJX44N6MF`):
five bookings at once for a one-seat workshop give one 201 and four `CAPACITY_REACHED`; two overlapping bookings of
a room at once, one `OVERLAP`; the same attendee twice, one `DUPLICATE`; a cancelled booking does not block its slot.
