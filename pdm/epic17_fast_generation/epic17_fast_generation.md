# Epic 17 — Fast generation: section renderer, component cache, templated CRUD

## Overview

Generation is slow because nearly all of its time is spent in engine (CLI) calls, often for code that is the
same from site to site. Measured on the last real runs (Antigravity, 2026-10-27):

| Run | Total | Engine calls | Checks | Repair |
|---|---|---|---|---|
| static, 5 pages (`gen_01M5YC5M…`) | ~25 min | 1 173 s: shell 418 s, then 5 pages **one after another** (96–226 s each) | 78 s (47 s `pnpm install`) | 226 s for a `conventions` failure |
| backend (`gen_01M5XTFV…`) | ~17 min | 772 s: database 185 s, backend 460 s, tests 127 s | 23 s | 197 s for a `lint` failure |

In dynamic mode the lanes run in parallel (Epic 14), so the slower lane sets the total — on these numbers the
**frontend** lane.

The FrontendSpec is already a JSON tree (site → pages → sections → content) over a closed catalogue of 15
section components (`BUILTIN_SECTIONS`). Today the engine is asked to turn that JSON into JSX on every run; it
acts as a slow, non-deterministic compiler. This epic makes that step a **renderer**: the section library is
written and tested once in our overlay, and each generation writes data (`src/content/site.json`) plus thin
route files. The engine is called only for what the catalogue cannot express, and what it writes is **cached**
by content so the same component is never generated or tested twice. The backend gets the same treatment for
CRUD: modules from templates, the engine only for custom operations and rules.

```
 FrontendSpec ─▶ validate (typed section props, 17.1)
      │
      ├─ catalogue sections ───────────────▶ site.json + route files (deterministic, 17.2 / 17.4)
      │                                          └─▶ <PageRenderer> ─▶ registry ─▶ <SectionRenderer> (recursive on layout children)
      └─ custom components ─▶ cache lookup ─┬─ hit  ─▶ cached files, no engine call, no isolated checks
                                (17.3)      └─ miss ─▶ one engine call per component, in parallel
                                                         ─▶ isolated checks ─▶ store in cache
 BackendSpec ─▶ CRUD modules from templates (17.6) ─▶ engine only for custom operations / rules
 both lanes  ─▶ auto-fix (ruff --fix, eslint --fix) and pre-installed dependencies before checks (17.5)
```

Recursion is limited on purpose: only **layout nodes** (`Columns`, `Stack`, `Grid`, `Tabs`) have `children`, and
their children are sections. The spec does not describe HTML elements (no `div → div → p` trees): that is JSX
written as JSON, which models fill badly and which is hard to validate.

What changes for the user: catalogue-only sites look like the catalogue (less bespoke than engine-written
pages); custom components still give room for anything else. Later epics get simpler: Epic 15 assets become
props of sections; Epic 16 revisions become a JSON patch and a re-render (feedback on a catalogue section
included, the engine only for custom components), and inspect mode (16.4) maps a click to one node of the spec.

**Requirements:** FR-30 (fast generation and reuse) — requirements v1.4

## Stories

| # | Story | Depends on |
|---|---|---|
| 17.1 | [Typed section props & layout nodes](story17.1_section_props.md) | 12.1 |
| 17.2 | [Section renderer for static sites](story17.2_section_renderer.md) | 17.1, 13.2 |
| 17.3 | [Custom components: parallel engine calls & component cache](story17.3_component_cache.md) | 17.2 |
| 17.4 | [Data sections for dynamic apps](story17.4_data_sections.md) | 17.2, 13.2 (client + mocks) |
| 17.5 | [Auto-fix and pre-installed dependencies](story17.5_faster_checks.md) | 6.2, 13.4 |
| 17.6 | [Backend CRUD from templates](story17.6_backend_crud_templates.md) | 5.3, 12.3 |

17.5 is independent and can go first; it pays off for every mode at once.

## Epic acceptance

- `static-landing` and `project-tracker-dynamic` (catalogue-only) generate with **no engine call** on the
  frontend lane; the frontend lane of `static-landing` takes under 3 minutes in Docker, checks and preview
  included.
- `shop-dynamic` makes one engine call per custom component (3), run in parallel; generating it a second time
  makes **none** (all cache hits) and skips their isolated checks.
- A backend for `two-entity` (CRUD only) generates with no engine call for its modules; validation still passes
  with the same checks as today.
- The existing checks, previews, live switch (Epic 14) and artifacts keep working; the fake engine and golden
  projects are updated and listed in `docs/development/test-doubles.md`.
- Timings before and after are recorded in each story's Status note (fake engine for the deterministic parts;
  one paid real-engine run only when the user asks).
