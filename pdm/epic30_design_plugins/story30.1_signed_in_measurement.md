# Story 30.1 — Measure apps signed in

**Epic:** [30 — Design plugins](epic30_design_plugins.md) · **Requirements:** FR-44, FR-37 · **Depends on:** 23.12

## User story

As the person adding design plugins, I want a report that compares apps as their users see them, signed in, by
structure and by screen, so that I can tell which plugins make apps more different and which gaps remain.

## Context

- `make app-design-report` (23.1, `scripts/app_design_report`): golden apps, 64×40 greyscale first screens, distinct
  frames; Story 23.12 found the greyscale score measures white space and that secured apps were shot on the sign-in
  page.
- The prototype harness (23.0) already signs in as each demo user.

## Steps

1. **Signed in, per area:** the report signs in as one demo user per area (the auth plugin's demo accounts, on mocks)
   and shoots home, the main list and one record, at 1440 and 375 px, light.
2. **Structural fingerprint** per screen, read from `app.json` and the DOM markers (`data-bga-view`, the shell, the
   detail view, the card anatomy once 30.4 adds its marker): distinct fingerprints across the golden set, and the pairs
   that share one.
3. **Screen similarity** on edge maps (layout lines, not colour masses) of the signed-in screens; the greyscale score
   stays in the report for comparison.
4. **Coverage:** which registry values (shells, views, details, homes, cards, recipes) the golden set uses, so unused
   plugins show.
5. **Baseline** on today's kit, stored in this Status and in `.data/reports/app-design/<date>/`.
6. Tests: the fingerprint and the edge similarity on recorded screenshots.

## Acceptance criteria

- [ ] The report shoots signed-in screens for every area of every golden app.
- [ ] It lists structural fingerprints, similar pairs and unused values.
- [ ] The baseline is recorded here.

## Verify

`make app-design-report`, `make test`.

## Status

Proposed 2026-11-08.
