# Story 9.10 — Usage & traces page

**Epic:** [9 — Agent UI](epic9_agent_ui.md) · **Requirements:** FR-13, FR-18 · **Depends on:** 8.4, 9.4

## User story

As a user, I want one place in the navigation that shows how much time, how many model calls and how much money
my generations used, and where (which nodes, engines and models), so that I can compare runs and engines.

## Acceptance criteria

- [x] Sidebar entry **Usage & traces** (`/usage`), next to Generations and New generation.
- [x] Summary tiles for the selected period (default 7 days): generations, success rate, total wall time,
      model calls, tokens, cost (reported + *estimated*), average cost and duration per completed generation.
- [x] Charts: cost and duration per day; breakdown by engine, by model, by node (which node is the most expensive
      or slowest on average), by lane; repair attempts per generation.
- [x] Table of generations with mode, engine, status, duration, model calls, tokens, cost and a link to its Trace
      tab (9.4) and LangSmith run; sortable, filterable by engine / mode / status / period.
- [x] Owner-scoped (admins can switch to all users). Data from a new `GET /api/v1/usage?from&to&groupBy=` that
      aggregates the 8.4 rollups (no LangSmith dependency).

**Status (2026-10-27):** done (`/usage`, `features/usage/`, `GET /api/v1/usage`). Notes:
- `GET /api/v1/usage?from&to&scope=mine|all` returns every breakdown at once (day, engine, mode, model, node,
  lane, generations) instead of a `groupBy` parameter; at most 1,000 generations per period (`truncated`).
- Periods are presets (7 / 30 / 90 days). Charts use the shadcn chart component (recharts); each breakdown has a
  table under it, and cost per day stacks reported and estimated cost.
- Node breakdown shows per-generation averages, so the costliest or slowest node stands out.
