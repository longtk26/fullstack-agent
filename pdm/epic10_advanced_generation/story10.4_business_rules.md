# Story 10.4 — Declarative business rules

**Epic:** [10 — Advanced generation](epic10_advanced_generation.md) · **Requirements:** FR-07 · **Depends on:** 10.3

## User story

As a spec author, I want common business rules expressed declaratively and generated reliably, and complex ones
implemented by the engine with tests, while ambiguous ones are flagged rather than guessed; as a user of the app, I
am only offered what the rules allow.

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

Frontend (dynamic mode):

- [ ] The contract exposes `transition` and `immutableAfter` rules (`x-bga.rules`); a status field offers only the
      allowed next states, and edit and delete actions are hidden on locked records.
- [ ] MSW enforces the deterministic rules with the same error codes, so journeys see the same rejections on mocks
      and live; a rejection shows on its field (10.0a).

## Status

**Planned (2026-11-04)**, revised from the first Epic 10 (plugin, frontend half, mocks).
