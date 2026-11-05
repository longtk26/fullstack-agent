# Story 10.4 — Declarative business rules

**Epic:** [10 — Advanced generation](epic10_advanced_generation.md) · **Requirements:** FR-07 · **Depends on:** 10.3

## User story

As a spec author, I want common business rules expressed declaratively and generated reliably, and complex ones
implemented by the engine with tests, while ambiguous ones are flagged rather than guessed.

## Acceptance criteria

Backend (the `rules` plugin):

- [ ] Rules are enforced in use cases (use-case pre-check hook) and raise `BaseException` subclasses
      (`ConflictException` 409, `BadRequestException`, `ForbiddenException`) with an `ErrorCode` and the field in
      `details`. Predefined rule kinds use helpers in `src/libs/rules/` plus template tests:

| Kind | Example | Rejection |
|---|---|---|
| `transition` | status TODO→IN_PROGRESS→DONE, no going back | 409 `INVALID_TRANSITION` |
| `immutableAfter` | order cannot be cancelled after `SHIPPED` | 409 `RESOURCE_LOCKED` |
| `ownerOnly` | only the owner can update a task | 403/404 (reuses 10.3) |
| `sumEquals` | `order.total == sum(lineItems.price*qty)` | 422 `TOTAL_MISMATCH` |

- [ ] `kind=custom` rules (free-text description) are implemented by the engine in the use case, with the rules API in
      its context pack and required tests for the expected and rejected cases; the validation smoke call covers them.
- [ ] If a custom rule is ambiguous (the engine flags it, or the description lacks the actors or states it needs), it
      is **not implemented**. It is recorded in `unresolved` with the reason, and the operation's OpenAPI description
      notes it.
- [ ] Rule ids appear in test names and in the manifest.

Contract:

- [ ] One definition per rule in the plan; codegen writes from it the use-case check, the `allowedActions` entries
      (`transition:<STATE>` for the allowed next states; no `update` or `delete` on a locked record), the MSW
      behaviour and the scenarios (an allowed and a refused transition, an edit of a locked record).
- [ ] Every rule's code is in `x-bga.errors` with its field; `kind=custom` rules too (code and field from the
      planner), so the app shows them on the field
      ([22.7](../epic22_dynamic_app_frontend/story22.7_plugin_frontends.md)).
- [ ] `x-bga.rules` still describes the rules, for documentation and the try-it explorer; frontends act on
      `allowedActions`, not on it.

## Status

**Planned (2026-11-04)**, revised from the first Epic 10 (plugin). Frontend half and mocks moved
to 22.7 on 2026-11-05.
