# Story 10.4 — Declarative business rules

**Epic:** [10 — Advanced generation](epic10_advanced_generation.md) · **Requirements:** FR-07 · **Depends on:** 10.3

## User story

As a spec author, I want common business rules expressed declaratively and generated reliably, and complex ones
implemented by the engine with tests, while ambiguous ones are flagged rather than guessed.

## Acceptance criteria

Backend (the `rules` plugin):

- [x] Rules are enforced in use cases (use-case pre-check hook) and raise `BaseException` subclasses
      (`ConflictException` 409, `BadRequestException`, `ForbiddenException`) with an `ErrorCode` and the field in
      `details`. Predefined rule kinds use helpers in `src/libs/rules/` plus template tests:

| Kind | Example | Rejection |
|---|---|---|
| `transition` | status TODO→IN_PROGRESS→DONE, no going back | 409 `INVALID_TRANSITION` |
| `immutableAfter` | order cannot be cancelled after `SHIPPED` | 409 `RESOURCE_LOCKED` |
| `ownerOnly` | only the owner can update a task | 403/404 (reuses 10.3) |
| `sumEquals` | `order.total == sum(lineItems.price*qty)` | 422 `TOTAL_MISMATCH` |

- [x] `kind=custom` rules (free-text description) are implemented by the engine in the use case, with the rules API in
      its context pack and required tests for the expected and rejected cases; the validation smoke call covers them.
- [x] If a custom rule is ambiguous (the engine flags it, or the description lacks the actors or states it needs), it
      is **not implemented**. It is recorded in `unresolved` with the reason, and the operation's OpenAPI description
      notes it.
- [x] Rule ids appear in test names and in the manifest.

Contract:

- [x] One definition per rule in the plan; codegen writes from it the use-case check, the `allowedActions` entries
      (`transition:<STATE>` for the allowed next states; no `update` or `delete` on a locked record), the MSW
      behaviour and the scenarios (an allowed and a refused transition, an edit of a locked record).
- [x] Every rule's code is in `x-bga.errors` with its field; `kind=custom` rules too: the planner gives each one an
      error code and a field, and the engine's note says to raise exactly that code (moved here from 10.0b), so the
      app shows them on the field
      ([22.7](../epic22_dynamic_app_frontend/story22.7_plugin_frontends.md)).
- [x] `x-bga.rules` still describes the rules, for documentation and the try-it explorer; frontends act on
      `allowedActions`, not on it.

## Status

**Done (2026-11-05)** on `feat/epic10-backend-plugins`. Planned 2026-11-04; frontend half and mocks moved to 22.7 on
2026-11-05.

- **The `rules` plugin** (`orchestrator/plugins/rules.py`, `templates/plugins/rules`; on when an operation names a
  rule other than `ownerOnly`). One definition per rule in the plan (`op.ruleChecks`); from it: a constant per rule in
  the generated `src/libs/rules/catalog.py` (on `Transition`, `ImmutableAfter`, `SumEquals` from
  `src/libs/rules/kinds.py`), the use-case check (pre-check hook, after the policies' ownership check, so another
  user's record is still a 404), `allowedActions`, the template tests, the contract's errors and scenarios.
- **Kinds**: `transition` (update; 409 `INVALID_TRANSITION`, details `from`, `to`, `allowed`; keeping the state is
  allowed); `immutableAfter` (update and delete; 409 `RESOURCE_LOCKED`); `sumEquals` (update; 422 `TOTAL_MISMATCH`)
  with params defined now: `items` (an entity whose rows reference the record), `itemField`, optional
  `quantityField`; the validator checks them. A new hook, `repository_methods`, adds the sum query
  (`tasks_total(project_id)`). The three codes are in the overlay's `ErrorCode`. `ownerOnly` is ownership, written by
  the policies plugin (an operation may now have a role policy and an `ownerOnly` rule together).
- **`allowedActions`**: `transition:<STATE>` for every reachable state, listed when the record's state allows it;
  no `update` or `delete` on a locked record. Without auth the DTO's `allowed_actions(entity)` reads the state only;
  with policies both conditions apply (a transition inherits update's).
- **Custom rules**: the planner gives each one an error code (`params.code`, else the id in UPPER_SNAKE), a status
  (`params.status`, default 409) and a field (`params.field`); they are in the operation's errors and the contract
  with the rule's description, the engine's context pack shows them with their answer, and its note says to raise
  exactly that code with tests for an accepted and a refused case. The operation's success scenarios accept the rule's
  answer as well (`expect.or`), so the smoke check proves the operation answers one way or the other.
- **Ambiguous custom rules** (`params.ambiguous`, or a description under five words) are not implemented: no engine
  gap, an `unresolved` entry with the reason, and the operation's OpenAPI description says so.
- **Template tests**, named after the rule: allowed and refused transition, edit and delete of a locked record, a
  matching and a mismatching total. The generic update test no longer picks a field a rule checks.
- **Contract**: each rule's error in `x-bga.errors` with `rule` and `fields`; scenarios "refused transition",
  "allowed transition" (refused first: the allowed one changes the seeded record), "locked record", "total mismatch";
  earlier scenarios that would reach a locked record move to an open one; `x-bga.rules` lists every rule with its
  operations and who implements it (`template`, `engine`, `none`). The manifest lists the same, and each operation's
  rule ids.

**Deviations:**

- The engine does not flag ambiguity itself yet: the check is the description's length or `params.ambiguous` (which a
  draft can set). Whether the engine wrote the custom rule's tests is not checked; the smoke check's `expect.or` is.
- The predefined kinds check updates (and deletes); creating a record is not checked (a transition has no "from"; a
  new record has no items to sum). A rule named on another operation is recorded in `unresolved` as checking nothing.
- `sumEquals` checks the parent's field when it is sent; changing an item does not recompute or re-check the parent.
- MSW does not apply the rules yet (22.7); the contract carries what it needs (`x-bga.rules`, `allowedActions`).

**Verified:** `make lint`; `tests/test_rules.py` (9) and the policies, codegen, packaging and completion tests;
`make test` (all pass); `BGA_SANDBOX_TESTS=1` for a rules generation through the workflow
(`test_a_backend_with_business_rules_passes_its_tests_and_scenarios`): every check passes on the first try, 37
template tests, 24 scenarios, 11 operations matching. `make up`, then a fake-engine backend generation of the rules
spec (`gen_01M6N44H9BF1N8H8PZHM2SZ3XT`): a new task lists `transition:IN_PROGRESS` only; TODO → DONE is 409
`INVALID_TRANSITION` with `from`, `to` and `allowed`; TODO → IN_PROGRESS → DONE succeed and the done task lists no
actions; editing or deleting it is 409 `RESOURCE_LOCKED`; with tasks of 3 and 4 points, `totalPoints: 8` is 422
`TOTAL_MISMATCH` (expected 7.00) and 7 is accepted. The ambiguous rule's note is in the route's OpenAPI description
(added after the live run; checked by test and the sandbox).
