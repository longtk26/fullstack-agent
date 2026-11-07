# Story 25.5 — Demo data linked to the demo users

**Epic:** [25 — App correctness](epic25_app_correctness.md) · **Requirements:** FR-39 · **Depends on:** 25.2

## User story

As a business owner trying the POC, I want to sign in as each demo user and find records that are mine, so every
role's workflow can be shown right away.

## Context

- F4: the seed made person-tied parent records owned by user ids that are no demo account, so the demo user of that
  role had nothing of their own to start the workflow from; listing them as that user returned everyone's (F1 again).
- Demo users come from the auth plugin (10.2: one `demo-<role>@example.com` per role); the seed comes from the
  contract's fixtures (`build_fixtures`, `build_contract_seed`).

## Steps

1. **Demo users in the fixtures.** The fixtures know the demo users' ids (stable ids, as the seed's), and every
   person-tied record (25.2) in the seed belongs to a demo user of the person's role; a second demo user per role whose
   records are private (`demo-<role>-2@example.com`), so "another user" can be shown and checked.
2. **Assignments.** Records assigned to a worker role (25.2 step 3) are assigned to the demo worker in part of the
   seed, so the worker's list is not empty.
3. **The sign-in page** lists both demo users per role (22.7 already lists them).
4. Tests on synthetic specs (a direct owner, an owner through a parent, an assignee): each demo user of the owner's
   role owns at least one record; the second user owns others; seed inserts (the smoke check's seed rule).

## Acceptance criteria

- [ ] Each demo user of a person role owns at least one record of each person-tied entity in the seed.
- [ ] The second demo user of a role exists, and its records are hidden from the first (with 25.2).
- [ ] The backend smoke check's seed rule still passes.

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test`, 25.6.
