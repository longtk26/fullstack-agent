# Story 9.8 — Parallel run view & live-API switch

**Epic:** [9 — Agent UI](epic9_agent_ui.md) · **Requirements:** FR-18, FR-27 · **Depends on:** 9.3, 14.1, 14.2

## User story

As a user, I want to watch the frontend and backend being built side by side and see when my frontend moves
from mock data to the real API.

## Acceptance criteria

- [ ] Detail page shows lanes (`frontend`, `backend`, `integration`) with their own status badge, current step and
      repair attempts; the workflow diagram renders the parallel graph (14.1) with both lanes live.
- [ ] Event log filter by lane.
- [ ] Frontend preview card: link + embedded preview, a badge **Mock API** / **Live API**, the backend URL in use,
      and buttons *Re-check backend* / *Use mocks* (14.2).
- [ ] `COMPLETED_WITH_WARNINGS` banner explains why the frontend stayed on mocks.
