# Story 13.1 — Frontend planner

**Epic:** [13 — Frontend generation](epic13_frontend_generation.md) · **Requirements:** FR-25 · **Depends on:** 12.1, 12.3

## User story

As the frontend lane, I want an exact, reviewable file plan derived from the FrontendSpec, so that generation
has a fixed scope and the checks know what must exist.

## Acceptance criteria

- [x] Pure function `plan_frontend(frontendSpec, contract?) → FrontendPlan` (no LLM), saved as `.bga/frontend-plan.json`:
  - `routes[]`: page id → `src/app/<route>/page.tsx` (dynamic segments `[id]`), title, layout
  - `components[]`: composite components with file paths (`src/features/<domain>/components/<Name>.tsx`),
    companion hooks (`use-<name>.ts`) when they fetch or hold logic (skill rule: > 30 lines → hook)
  - `shadcn[]`: primitives to install (`pnpx shadcn add …`), from `components[].uses`
  - `theme`: token values for `globals.css` (light and dark)
  - `data[]`: per binding, the contract operation, generated client function, React Query key and hook name
  - `forms[]`: RHF + Zod schema names derived from the request schema
  - `tests[]`: one smoke test per route (renders, shows data or content, no console errors) and one per form
- [x] Deterministic (snapshot tests per example spec); naming follows nextjs-skills (`T`-prefixed types,
      `<Name>Props`, named React imports).

**Status (2026-10-27):** done. `src/orchestrator/frontend_planner.py` (`plan_frontend(spec, contract)`),
`frontend_theme.py` (tokens), snapshots `tests/fixtures/frontend-plans/`. Notes and deviations:
- Built-in sections (Hero, CardGrid, DataTable, Form, …) are shared and presentational: they go to
  `src/components/sections/<Name>.tsx` without a hook, and pages pass their data in. Declared composites go to
  `src/features/<domain>/components/` (domain = the contract module of their first binding) with a companion
  `use-<name>.ts` hook when they fetch or hold a form.
- `shadcn[]` is the closure of the primitives the components use plus what those primitives import (read from the
  pinned base), and the primitives forms, navigation and the sidebar shell need.
- `theme`: light and dark token sets derived from the spec's brand colours (foregrounds picked for contrast,
  muted text ≥ 3:1, body text ≥ 4.5:1); `dark` only for `light-dark` / `dark` schemes; fonts as CSS stacks (no
  font download, so builds work offline).
- `data[]` names the generated client function, React Query hook and key factory per binding; `forms[]` the Zod
  schema, values type and mutation hook; `tests[]` one smoke test per route (with a concrete URL from the
  contract fixtures or content for routes with parameters) and one per form.
