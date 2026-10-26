# Story 12.2 — Generation modes & job model

**Epic:** [12 — Modes, FrontendSpec & contract](epic12_contract_and_frontend_spec.md) · **Requirements:** FR-21 · **Depends on:** 4.1

## User story

As a user, I want to choose whether I am building a static site, a dynamic web app (frontend + backend), or only
an API, and see one job that tracks every part of it.

## Acceptance criteria

- [ ] `POST /api/v1/generations` accepts `mode: "backend" | "static" | "dynamic"` (default `backend`, so the
      existing API keeps working) and the inputs that mode needs:
  - `backend`: `backendSpec` | `specId` (unchanged)
  - `static`: `frontendSpec` | `frontendSpecId`
  - `dynamic`: `frontendSpec` + `backendSpec` (or their ids)
  Missing or extra inputs → 422 `MODE_INPUT_MISMATCH`.
- [ ] One generation row with an overall `status` plus **lane statuses**: `lanes: {backend?, frontend?,
      integration?}` each `PENDING | RUNNING | VALIDATING | REPAIRING | COMPLETED | FAILED | SKIPPED`. Overall
      status rules: all required lanes COMPLETED → COMPLETED; the backend failing in `dynamic` mode → overall
      `COMPLETED_WITH_WARNINGS` when the frontend still works on mocks (14.2), otherwise FAILED.
- [ ] Events carry `lane` (`backend` | `frontend` | `integration`); the SSE stream and the detail API expose them.
- [ ] Options per lane: backend options as today; frontend options `{ runTests, generatePreview, mockApi }`.
- [ ] Migration for the new columns; the list endpoint shows mode and lane badges.
