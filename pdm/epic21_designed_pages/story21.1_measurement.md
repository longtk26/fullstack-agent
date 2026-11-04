# Story 21.1 — Measurement: section pages against designed pages

**Epic:** [21 — Designed pages](epic21_designed_pages.md) · **Depends on:** 21.6, 18.10

## What to measure (needs the user's yes: paid API calls)

The same five requirements (`examples/requirements/`: `northwind-studio.md`, `corner-shop.md` as static;
`project-tracker.md`, `clinic-booking.md`, `shop-orders.md` as dynamic), each drafted twice with the Gemini API
engine: `FRONTEND_TREES=false` (section pages) and `FRONTEND_TREES=true` (designed pages), the same `designSeed`.

| Measure | How |
|---|---|
| Draft time and cost | the draft's `usage` (per call: `draft_frontend_spec`, `draft_tree` × pages) |
| Validity | drafts `SUCCEEDED` vs `NEEDS_REVIEW`; trees dropped (the "dropped" notes) |
| Design check | `make design-check-fixture ARGS="--spec <draft frontend-spec> [--backend <backend-spec>] --motion"` on each draft: failures per view |
| Looks designed | screenshots of the home page at 1440 px side by side; first-screen similarity between the two modes (the diversity report's measure) |
| Data | every data component bound (`data-bga-records` > 0 on the built pages) |

## Acceptance criteria

- [ ] Designed pages validate as often as section pages and pass the design check with no more failures.
- [ ] Draft time stays within the targets of 18.10 (≤ 180 s dynamic, ≤ 120 s static) with the tree calls.
- [ ] The home pages of the five requirements look designed (reviewed side by side; the user decides).

## Status

**Ready to run (2026-11-04)**; waits for the user's yes. The user planned to review static and dynamic generations
with `make up` first.
