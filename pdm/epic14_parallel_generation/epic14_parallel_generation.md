# Epic 14 — Parallel generation & live-API switch

## Overview

In `dynamic` mode the frontend and backend lanes run **at the same time**, joined by the contract (12.3).
The frontend is built and tested against mocks (`MOCK_TEST_API=true`). When the frontend lane finishes, an
integration step checks the backend: if the backend generation is COMPLETED and its preview container answers
`/health`, the frontend preview is switched to the real API (`MOCK_TEST_API=false`, `API_BASE_URL=<backend
preview URL>`) and a live smoke test runs. If the backend is not healthy, the frontend keeps working on mocks
and the job reports why.

**Requirements:** FR-27 (parallel generation & integration) — requirements v1.2

```
                         ┌─ backend lane:  validate_spec → plan → generate_database → generate_backend → … → package → deploy_preview
 validate_inputs ─ contract ┤
                         └─ frontend lane: frontend_plan → frontend_scaffold → generate_frontend → validate_frontend ⇄ repair → package → deploy_preview_fe
                                                                                                         │
                                       integrate: wait backend (COMPLETED + /health) ─▶ MOCK_TEST_API=false ─▶ live smoke
                                                     └── not healthy / timeout ─▶ keep mocks, COMPLETED_WITH_WARNINGS
```

## Stories

| # | Story | Depends on |
|---|---|---|
| 14.1 | [Parallel workflow (fork / join lanes)](story14.1_parallel_workflow.md) | 12.2, 12.3, 4.3 |
| 14.2 | [Backend readiness check & `MOCK_TEST_API` switch](story14.2_mock_api_switch.md) | 14.1, 13.5, 7.3 |
| 14.3 | [Live integration smoke test](story14.3_integration_smoke.md) | 14.2 |

## Epic acceptance

- A `dynamic` generation of `examples/frontend-specs/shop-dynamic.json` runs both lanes concurrently (visible in
  the UI), the frontend preview first serves mock data, and after the backend preview is healthy the same pages
  show the backend's seed data with `MOCK_TEST_API=false`; the live smoke test passes.
- Killing the backend preview before the switch leaves the frontend on mocks, with the overall status
  `COMPLETED_WITH_WARNINGS` and a re-check button in the UI.
