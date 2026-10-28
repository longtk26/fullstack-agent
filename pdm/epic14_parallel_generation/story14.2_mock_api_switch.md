# Story 14.2 — Backend readiness check & `MOCK_TEST_API` switch

**Epic:** [14 — Parallel generation](epic14_parallel_generation.md) · **Requirements:** FR-27 · **Depends on:** 14.1, 13.5, 7.3

## User story

As a user, I want my frontend to start on mock data and move to the real backend automatically as soon as the
backend is ready, without rebuilding the frontend.

## Acceptance criteria

- [x] After the frontend lane completes, node `integrate` checks the backend lane: status COMPLETED **and** the
      backend preview's `GET /health` → 200 **and** `GET /openapi.json` matches the contract sha.
      It waits up to `INTEGRATION_WAIT_SECONDS` (default 900) while the backend lane is still running.
- [x] Healthy → restart the frontend preview with `MOCK_TEST_API=false` and `API_BASE_URL=<backend preview URL>`;
      the runtime config (13.2) picks it up without a rebuild; event `integration.switched_to_live`.
- [x] Not healthy (backend FAILED, preview not running, timeout) → keep `MOCK_TEST_API=true`, record the reason,
      overall `COMPLETED_WITH_WARNINGS`; event `integration.kept_mocks`.
- [x] `POST /api/v1/generations/{id}/integration/recheck` repeats the check later (e.g. after a backend
      preview restart) and switches if healthy; `POST …/integration/use-mocks` switches back.
- [x] The downloadable frontend's `.env.ex` documents `MOCK_TEST_API` and `API_BASE_URL`.

**Status (2026-10-28):** done. When each lane passes validation in dynamic mode, `package_lane_preview`
(`src/orchestrator/integration.py`) packages its source ZIP (`frontend.zip`, `backend.zip`, `seed.json` built from
`contract["x-bga"]["fixtures"]`) and starts its preview container (`MOCK_TEST_API=true` initially for the frontend),
and `validate_frontend` starts the `INTEGRATION_WAIT_SECONDS` watchdog (`config.integration_wait_seconds = 900`) so a
stalled backend lane is aborted after the timeout. Node `integrate` runs `check_backend_ready` (verifying `backend`
lane `COMPLETED`, `GET /health` → 200, and `GET /openapi.json` contract sha / conformance via `verify_openapi_matches_contract`).
If healthy, `PreviewService.switch_frontend` restarts the frontend preview container with `MOCK_TEST_API=false` and
`API_BASE_URL=<backend preview URL>` (restarting the backend preview if needed so its `CORS_ORIGINS` includes the
frontend preview port) and emits `integration.switched_to_live`. Otherwise it keeps `MOCK_TEST_API=true`, emits
`integration.kept_mocks` with the reason, sets the `integration` lane `SKIPPED`, and finishes `COMPLETED_WITH_WARNINGS`.
`POST /api/v1/generations/{id}/integration/recheck` and `POST /api/v1/generations/{id}/integration/use-mocks`
(`src/modules/previews/presenter/router.py` → `PreviewService.recheck` / `use_mocks`) allow re-running the check or
switching back to mocks on demand.
