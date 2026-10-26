# Story 13.5 — Frontend packaging & preview container

**Epic:** [13 — Frontend generation](epic13_frontend_generation.md) · **Requirements:** FR-26, FR-16 · **Depends on:** 13.4, 7.3

## User story

As a user, I want the generated frontend running at a local URL right away, and downloadable as a project.

## Acceptance criteria

- [ ] Artifacts: `frontend.zip`, `frontend-spec.json`, `frontend-plan.json`, build report; manifest gains a
      `frontend` section (mode, routes, theme, contract sha in `dynamic` mode).
- [ ] Preview container `preview-fe-<gen>` on a free port from `PREVIEW_PORT_RANGE`, bound to `127.0.0.1`:
  - `static`: nginx serving the export;
  - `dynamic`: the Node standalone server with `MOCK_TEST_API=true` and `API_BASE_URL` empty until 14.2 switches it.
- [ ] The backend preview's `CORS_ORIGINS` includes the frontend preview origin.
- [ ] Lifecycle (stop, restart, delete, TTL) shared with 7.4; `GET /generations/{id}` returns
      `preview.frontend: {status, url, mockApi}`.
