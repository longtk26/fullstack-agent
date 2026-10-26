# Story 14.3 — Live integration smoke test

**Epic:** [14 — Parallel generation](epic14_parallel_generation.md) · **Requirements:** FR-27, FR-11 · **Depends on:** 14.2

## User story

As a user, I want proof that the generated frontend really works against the generated backend, not only
against mocks.

## Acceptance criteria

- [ ] After switching to live, the Node sandbox runs the frontend's Playwright smoke tests against the frontend
      preview with the live API: every page renders without console errors; every data-bound section shows
      backend data (seed records); every form submits successfully and the result is visible.
- [ ] Live responses are validated against the contract schemas (a mismatch names operation and field).
- [ ] Results in `integration` checks of the report; failures do **not** regenerate either side automatically
      (the contract is fixed); they are reported with the failing page, operation and response.
