# Story 21.7 — Design check and diversity report on designed pages

**Epic:** [21 — Designed pages](epic21_designed_pages.md) · **Depends on:** 20.1, 21.2

## Scope

- The section-library fixture's `/designed` page is measured by `make design-check-fixture` like every other page
  (overflow at 390 px, type sizes, families, contrast, light and dark, motion and no-JavaScript passes).
- `DESIGN_CHECKLIST.md` gains the designed-page rules and how the tree rules keep them.
- `make design-diversity` drafts with the fake engine; with `FRONTEND_TREES=true` (the default outside the tests)
  its drafts carry trees and the first-screen screenshots measure the designed home pages.

## Acceptance criteria

- [x] The design check runs on the designed page and reports its rules.
- [ ] The diversity report's first-screen similarity is measured on designed pages (run with the real engine, 21.1).

## Status

**Done (2026-11-04)** for the fixture and the checklist. The playful run of the fixture (`.data/shots/epic21-designed`)
reported the designed page's deviations: `font-mono` → `ui-monospace` not loaded (fixed in the fixture, forbidden by
the prompt), the headline at 3–4 lines on a phone (the prompt asks for `text-4xl md:text-6xl`), 7 type sizes (the
prompt caps at 6).
