# Story 22.8 — Design checks, measurement and switch-over

**Epic:** [22 — Dynamic app frontend](epic22_dynamic_app_frontend.md) · **Requirements:** FR-36 · **Depends on:** 22.7

## User story

As the user of the agent, I want to see the new app flow beat the old one on real requirements before the old one is
removed from dynamic mode.

## Steps

1. **Measure** (with the user's yes, paid engine for drafts only): book club, flashcards, project-tracker and
   workshop-bookings on both flows (`DYNAMIC_FRONTEND=app` and `legacy`): draft time and calls, frontend lane time and
   engine calls, operations reachable, id inputs, design-check findings.
2. **Screenshots** of each app's list, detail, form and dashboard in light and dark at 375 px and 1440 px, side by
   side with the legacy flow, for the user's review.
3. **Switch-over**, after the user accepts: remove the legacy dynamic path (trees, direction cards, Manage area and
   journey drafting for dynamic specs); keep everything static uses. Old dynamic generations still open and download.
4. **Docs**: requirements, `agent-api/CLAUDE.md`, the backlog and the agent UI's mode description.

## Acceptance criteria

- [ ] The measurement table is in this story's Status, with the run ids.
- [ ] The user accepted the screenshots.
- [ ] After the switch-over, `DYNAMIC_FRONTEND` is gone; dynamic drafts use the app flow; static golden passes.

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test`; `make up`, one static and one dynamic generation on the
fake engine.

## Status

**Planned (2026-11-05).**
