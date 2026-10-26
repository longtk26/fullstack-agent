# Story 13.1 — Frontend planner

**Epic:** [13 — Frontend generation](epic13_frontend_generation.md) · **Requirements:** FR-25 · **Depends on:** 12.1, 12.3

## User story

As the frontend lane, I want an exact, reviewable file plan derived from the FrontendSpec, so that generation
has a fixed scope and the checks know what must exist.

## Acceptance criteria

- [ ] Pure function `plan_frontend(frontendSpec, contract?) → FrontendPlan` (no LLM), saved as `.bga/frontend-plan.json`:
  - `routes[]`: page id → `src/app/<route>/page.tsx` (dynamic segments `[id]`), title, layout
  - `components[]`: composite components with file paths (`src/features/<domain>/components/<Name>.tsx`),
    companion hooks (`use-<name>.ts`) when they fetch or hold logic (skill rule: > 30 lines → hook)
  - `shadcn[]`: primitives to install (`pnpx shadcn add …`), from `components[].uses`
  - `theme`: token values for `globals.css` (light and dark)
  - `data[]`: per binding, the contract operation, generated client function, React Query key and hook name
  - `forms[]`: RHF + Zod schema names derived from the request schema
  - `tests[]`: one smoke test per route (renders, shows data or content, no console errors) and one per form
- [ ] Deterministic (snapshot tests per example spec); naming follows nextjs-skills (`T`-prefixed types,
      `<Name>Props`, named React imports).
