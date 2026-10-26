# Story 14.2 — Backend readiness check & `MOCK_TEST_API` switch

**Epic:** [14 — Parallel generation](epic14_parallel_generation.md) · **Requirements:** FR-27 · **Depends on:** 14.1, 13.5, 7.3

## User story

As a user, I want my frontend to start on mock data and move to the real backend automatically as soon as the
backend is ready, without rebuilding the frontend.

## Acceptance criteria

- [ ] After the frontend lane completes, node `integrate` checks the backend lane: status COMPLETED **and** the
      backend preview's `GET /health` → 200 **and** `GET /openapi.json` matches the contract sha.
      It waits up to `INTEGRATION_WAIT_SECONDS` (default 900) while the backend lane is still running.
- [ ] Healthy → restart the frontend preview with `MOCK_TEST_API=false` and `API_BASE_URL=<backend preview URL>`;
      the runtime config (13.2) picks it up without a rebuild; event `integration.switched_to_live`.
- [ ] Not healthy (backend FAILED, preview not running, timeout) → keep `MOCK_TEST_API=true`, record the reason,
      overall `COMPLETED_WITH_WARNINGS`; event `integration.kept_mocks`.
- [ ] `POST /api/v1/generations/{id}/integration/recheck` repeats the check later (e.g. after a backend
      preview restart) and switches if healthy; `POST …/integration/use-mocks` switches back.
- [ ] The downloadable frontend's `.env.ex` documents `MOCK_TEST_API` and `API_BASE_URL`.
