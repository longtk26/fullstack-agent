# Story 9.4 — Trace viewer

**Epic:** [9 — Agent UI](epic9_agent_ui.md) · **Requirements:** FR-13 · **Depends on:** 9.3, 8.3

## User story

As a user debugging a slow or failed run, I want a waterfall of every node, CLI call, tool use and check, with
their outputs, without leaving the app.

## Acceptance criteria

- [ ] Trace tab: collapsible span tree + time-axis waterfall bars, coloured by kind and status. Durations,
      plus tokens and cost on engine spans.
- [ ] Span detail drawer: attributes table, stdout/stderr excerpt viewer (tail, load more, copy), patch viewer for
      repair spans (diff highlighting), and a "Open in LangSmith" deep link when available.
- [ ] Filters: kind (node/engine/tool/check), errors only. Search by name or path.
- [ ] Live while running: open spans show a running timer and update on SSE.
