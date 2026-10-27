# Story 9.4 — Trace viewer

**Epic:** [9 — Agent UI](epic9_agent_ui.md) · **Requirements:** FR-13 · **Depends on:** 9.3, 8.3

## User story

As a user debugging a slow or failed run, I want a waterfall of every node, CLI call, tool use and check, with
their outputs, without leaving the app.

## Acceptance criteria

- [x] Trace tab header: total wall time, engine time vs sandbox time, number of model calls, tokens (input /
      output / cache), cost (reported + *estimated*), and a **per-node summary table** (node, attempts, duration,
      model calls, tokens, cost; sortable) with a bar showing each node's share of time and cost; in dynamic mode
      grouped by lane.
- [x] Collapsible span tree + time-axis waterfall bars, coloured by kind (lane, node, engine, model call, tool,
      check) and status; parallel lanes drawn on separate rows. Durations everywhere, tokens and cost on engine
      and model-call spans, model name on model-call spans.
- [x] Span detail drawer: attributes table, stdout/stderr excerpt viewer (tail, load more, copy), patch viewer for
      repair spans (diff highlighting), and a "Open in LangSmith" deep link when available.
- [x] Filters: kind (lane/node/engine/model call/tool/check), lane, errors only, slowest N. Search by name or path.
- [x] Live while running: open spans show a running timer and update on SSE.

**Status (2026-10-27):** done (`features/generations/components/trace/`, hooks `use-trace`, `use-trace-view`,
`use-span-output`). Notes:
- Kinds are coloured with the validated categorical palette (now the `--chart-1…6` tokens, light and dark),
  errors get a destructive ring and an icon, running spans pulse and tick; the legend and span names carry the
  kind, so colour is never the only cue.
- Model calls start folded (a real run has hundreds); filters and search unfold the matching path. Rows are
  virtualized. The detail view opens on a tab from `?tab=trace` (links from the usage page).
- "Open in LangSmith" opens the trace; spans have no per-span LangSmith link (their run ids are not stored).
- Lane grouping appears when a trace has more than one lane (Epic 14); backend-only traces have one.
