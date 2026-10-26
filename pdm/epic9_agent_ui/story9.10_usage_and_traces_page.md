# Story 9.10 — Usage & traces page

**Epic:** [9 — Agent UI](epic9_agent_ui.md) · **Requirements:** FR-13, FR-18 · **Depends on:** 8.4, 9.4

## User story

As a user, I want one place in the navigation that shows how much time, how many model calls and how much money
my generations used, and where (which nodes, engines and models), so that I can compare runs and engines.

## Acceptance criteria

- [ ] Sidebar entry **Usage & traces** (`/usage`), next to Generations and New generation.
- [ ] Summary tiles for the selected period (default 7 days): generations, success rate, total wall time,
      model calls, tokens, cost (reported + *estimated*), average cost and duration per completed generation.
- [ ] Charts: cost and duration per day; breakdown by engine, by model, by node (which node is the most expensive
      or slowest on average), by lane; repair attempts per generation.
- [ ] Table of generations with mode, engine, status, duration, model calls, tokens, cost and a link to its Trace
      tab (9.4) and LangSmith run; sortable, filterable by engine / mode / status / period.
- [ ] Owner-scoped (admins can switch to all users). Data from a new `GET /api/v1/usage?from&to&groupBy=` that
      aggregates the 8.4 rollups (no LangSmith dependency).
