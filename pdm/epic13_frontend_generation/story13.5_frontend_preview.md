# Story 13.5 — Frontend packaging & preview container

**Epic:** [13 — Frontend generation](epic13_frontend_generation.md) · **Requirements:** FR-26, FR-16 · **Depends on:** 13.4, 7.3

## User story

As a user, I want the generated frontend running at a local URL right away, and downloadable as a project.

## Acceptance criteria

- [x] Artifacts: `frontend.zip`, `frontend-spec.json`, `frontend-plan.json`, build report; manifest gains a
      `frontend` section (mode, routes, theme, contract sha in `dynamic` mode).
- [x] Preview container `preview-fe-<gen>` on a free port from `PREVIEW_PORT_RANGE`, bound to `127.0.0.1`:
  - `static`: nginx serving the export;
  - `dynamic`: the Node standalone server with `MOCK_TEST_API=true` and `API_BASE_URL` empty until 14.2 switches it.
- [x] The backend preview's `CORS_ORIGINS` includes the frontend preview origin.
- [x] Lifecycle (stop, restart, delete, TTL) shared with 7.4; `GET /generations/{id}` returns
      `preview.frontend: {status, url, mockApi}`.

**Status (2026-10-27):** done. `src/preview/docker_frontend_preview.py`, preview service and API by `kind`
(migration `a6f75b3fd70b`: `previews.kind`, `mock_api`, one row per generation and kind). Notes and deviations:
- Artifacts `frontend.zip`, `frontend-plan.json`, `frontend-validation-<n>.json`, `frontend-repair-<n>.patch`;
  `manifest.json` gains `frontend` (mode, routes, theme, contract sha, env); static generations get a manifest with
  only that section.
- Container `bga-preview-fe-<gen>` built from `frontend.zip` with the project's own Dockerfile (network at build
  time, like backend previews): static = nginx-unprivileged on 8080, dynamic = standalone Node server with
  `MOCK_TEST_API=true`, `API_BASE_URL` empty.
- A finished generation starts the frontend preview first, then the backend preview with `CORS_ORIGINS`
  including the frontend preview origin. `PREVIEW_MAX_RUNNING` counts generations, not containers.
- The API uses `?kind=frontend` on the preview endpoints; `GET /generations/{id}` returns `frontendPreview`
  (`{kind, status, url, mockApi, …}`) next to `preview` (backend) rather than `preview.frontend`. The UI shows
  **Open site** (with a "mock API" badge); the in-app App tab is 9.9.
