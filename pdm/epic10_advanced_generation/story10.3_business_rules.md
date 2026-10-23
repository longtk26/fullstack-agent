# Story 10.3 — Declarative business rules

**Epic:** [10 — Advanced generation](epic10_advanced_generation.md) · **Requirements:** FR-07 · **Depends on:** 10.2

## User story

As a spec author, I want common business rules expressed declaratively and generated reliably, and complex ones
implemented by the engine with tests, while ambiguous ones are flagged rather than guessed.

## Acceptance criteria

- [ ] Rules are enforced in use cases and raise `BaseException` subclasses (`ConflictException` 409,
      `BadRequestException`, `ForbiddenException`) with an `ErrorCode`. Predefined rule kinds use deterministic helpers
      (overlay `src/libs/rules/`) plus generated tests:

| Kind | Example | Rejection |
|---|---|---|
| `transition` | status TODO→IN_PROGRESS→DONE, no going back | 409 `INVALID_TRANSITION` |
| `immutableAfter` | order cannot be cancelled after `SHIPPED` | 409 `RESOURCE_LOCKED` |
| `ownerOnly` | only the owner can update a task | 403/404 (reuses 10.2) |
| `sumEquals` | `order.total == sum(lineItems.price*qty)` | 422 `TOTAL_MISMATCH` |

- [ ] `kind=custom` rules (free-text description) are implemented by the engine in the service layer, with required tests
      for the expected and rejected cases. The validation check verifies those tests exist (5.5 coverage check).
- [ ] If a custom rule is ambiguous (the engine flags it, or the description lacks the actors/states it needs), it is
      **not implemented**. It is recorded in `unresolved` with the reason, and the operation's OpenAPI description notes it.
- [ ] Rule ids appear in test names and in the manifest.
