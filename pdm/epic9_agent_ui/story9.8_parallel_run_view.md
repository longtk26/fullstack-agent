# Story 9.8 — Parallel run view & live-API switch

**Epic:** [9 — Agent UI](epic9_agent_ui.md) · **Requirements:** FR-18, FR-27 · **Depends on:** 9.3, 14.1, 14.2

## User story

As a user, I want to watch the frontend and backend being built side by side and see when my frontend moves
from mock data to the real API.

## Acceptance criteria

- [x] Detail page shows lanes (`frontend`, `backend`, `integration`) with their own status badge, current step and
      repair attempts; the workflow diagram renders the parallel graph (14.1) with both lanes live.
- [x] Event log filter by lane.
- [x] Frontend preview card: link + embedded preview, a badge **Mock API** / **Live API**, the backend URL in use,
      and buttons *Re-check backend* / *Use mocks* (14.2).
- [x] `COMPLETED_WITH_WARNINGS` banner explains why the frontend stayed on mocks.

**Status (2026-10-28):** done. `ParallelLanesCard` displays backend, frontend, and integration lanes with per-lane status,
current step, and repair loop attempt counters; `EventLog` filters by lane (`all`, `backend`, `frontend`, `integration`);
`FrontendPreviewCard` displays live/mock badge, backend URL in use, and integration re-check / use-mocks actions; and
`TerminalBanner` provides detailed explanation for mock API fallback on `COMPLETED_WITH_WARNINGS`.
