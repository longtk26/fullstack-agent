# Story 12.2 — Generation modes & job model

**Epic:** [12 — Modes, FrontendSpec & contract](epic12_contract_and_frontend_spec.md) · **Requirements:** FR-21 · **Depends on:** 4.1

## User story

As a user, I want to choose whether I am building a static site, a dynamic web app (frontend + backend), or only
an API, and see one job that tracks every part of it.

## Acceptance criteria

- [x] `POST /api/v1/generations` accepts `mode: "backend" | "static" | "dynamic"` (default `backend`, so the
      existing API keeps working) and the inputs that mode needs:
  - `backend`: `backendSpec` | `specId` (unchanged)
  - `static`: `frontendSpec` | `frontendSpecId`
  - `dynamic`: `frontendSpec` + `backendSpec` (or their ids)
  Missing or extra inputs → 422 `MODE_INPUT_MISMATCH`.
- [x] One generation row with an overall `status` plus **lane statuses**: `lanes: {backend?, frontend?,
      integration?}` each `PENDING | RUNNING | VALIDATING | REPAIRING | COMPLETED | FAILED | SKIPPED`. Overall
      status rules: all required lanes COMPLETED → COMPLETED; the backend failing in `dynamic` mode → overall
      `COMPLETED_WITH_WARNINGS` when the frontend still works on mocks (14.2), otherwise FAILED.
- [x] Events carry `lane` (`backend` | `frontend` | `integration`); the SSE stream and the detail API expose them.
- [x] Options per lane: backend options as today; frontend options `{ runTests, generatePreview, mockApi }`.
- [x] Migration for the new columns; the list endpoint shows mode and lane badges.

**Status (2026-10-27):** done. `generations.mode`, `frontend_spec_id`, `lanes` (JSON), `spec_id` nullable,
`generation_events.lane`, status `COMPLETED_WITH_WARNINGS` (migration `9371b02b939f`, existing rows backfilled
with a `backend` lane; downgrade deletes static generations). Rules in
`src/modules/shared/domain/generation_modes.py`. Notes and deviations:
- Lanes per mode: backend → `backend`; static → `frontend`; dynamic → `backend`, `frontend`, `integration`.
  Node → lane mapping: backend nodes → `backend`; `validate_inputs`, `build_contract`, `package_artifacts` are
  job-level (`lane: null`). Lane changes are `lane.changed` events and part of `status.changed` payloads.
- **Until Epics 13/14 exist** the frontend and integration lanes are set `SKIPPED` at job start (reason in the
  event), so a dynamic job ends `COMPLETED_WITH_WARNINGS` once its backend lane completes (error code
  `LANES_INCOMPLETE`, the reasons in `error`), and a static job validates and packages its FrontendSpec and
  ends `COMPLETED_WITH_WARNINGS` with no site. The backend preview still deploys for a dynamic job.
- The workflow graph is per mode (`GET /generations/graph?mode=`): backend = unchanged; dynamic =
  `validate_inputs → build_contract → plan_architecture → …`; static = `validate_inputs → package_artifacts`.
  14.1 turns the dynamic graph into parallel lanes.
- Frontend options live in `options.frontend` (`runTests`, `generatePreview`, `mockApi`, defaults true); they
  are stored for 13.x and dropped in backend mode. A FrontendSpec whose `project.mode` differs from the
  generation mode is also `MODE_INPUT_MISMATCH`. Both inline specs are stored even when invalid; the job reports
  them (as before for BackendSpecs).
- UI: mode badge and lane dots in the list, mode and lane badges plus a warnings banner on the detail page, the
  per-mode workflow diagram, readable `lane.changed` / `inputs.valid` / `spec.invalid` / `contract.ready` events.
  Creating static/dynamic jobs from the UI is 9.7a.

**Update (2026-10-27, Epic 13):** the frontend lane is real now; only the integration lane (Epic 14) is still
skipped, so static jobs end `COMPLETED` and dynamic jobs `COMPLETED_WITH_WARNINGS` until the live-API switch exists.
In dynamic mode the frontend lane runs after the backend lane (14.1 makes them parallel); a backend that hits the
repair limit no longer ends the job: the frontend still runs on mocks.

**Update (2026-10-28, Epic 14):** `UNAVAILABLE_LANES` is now empty. In dynamic mode both lanes run in parallel after
`build_contract`, followed by `integrate` (`Lane.INTEGRATION`). When `backend`, `frontend`, and `integration` all
complete, a dynamic job finishes `COMPLETED`; if `backend` or `integration` is `FAILED` or `SKIPPED` while `frontend`
is `COMPLETED`, it finishes `COMPLETED_WITH_WARNINGS`.
