# Story 9.3 — Live workflow step visualization

**Epic:** [9 — Agent UI](epic9_agent_ui.md) · **Requirements:** FR-09, FR-15 · **Depends on:** 9.1, 4.5

## User story

As a user, I want to see the LangGraph workflow as a diagram that lights up as the agent progresses, including
repair loops, so that I always know what is happening and why.

## Acceptance criteria

- [ ] Detail header: status badge, current step, engine, elapsed time, token and cost totals (live from
      `engine.usage`), **Cancel** button (confirm dialog → 4.6), LangSmith link.
- [ ] React Flow diagram from `GET /generations/graph`: node states `pending | running (animated) | passed | failed
      | skipped | cancelled`. The repair edge shows `attempt n / max`. Conditional edges are labelled.
- [ ] Clicking a node opens a drawer: attempts, timings, engine invocations (purpose, turns, tokens, exit), and the
      node's events.
- [ ] Event log panel: virtualized live list of SSE events (type icon, step, message, time), filter by type,
      auto-scroll toggle. It reconnects with `Last-Event-ID` and shows no duplicates.
- [ ] State handling: a `use-generation-stream.ts` hook merges SSE into the React Query cache. The page is correct
      after a hard refresh mid-run, because it replays from the start.
- [ ] Terminal states show a banner (COMPLETED → links to Results and API, FAILED → error summary + diagnostic report link).
