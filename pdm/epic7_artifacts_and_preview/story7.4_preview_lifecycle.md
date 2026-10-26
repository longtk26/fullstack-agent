# Story 7.4 — Preview lifecycle management

**Epic:** [7 — Artifacts & preview](epic7_artifacts_and_preview.md) · **Depends on:** 7.3 · **Decision:** Q6

## User story

As the operator, I want to start, stop and clean up preview containers, so that my machine doesn't fill up with
old backends.

## Acceptance criteria

- [x] `POST /api/v1/generations/{id}/preview/start | stop | restart`, `DELETE /api/v1/generations/{id}/preview`
      (removes the container, DB volume and image). `POST .../preview/reset-db` drops and recreates the preview DB.
- [x] `GET /api/v1/previews` lists the owner's previews with status, port and expiry.
- [x] `POST /api/v1/generations/{id}/preview/touch` refreshes `last_accessed_at` and extends the expiry (called by the UI try-it, 9.6).
- [x] Limits: `PREVIEW_MAX_RUNNING` (3). Starting another stops the least recently used one (or 409 when
      `PREVIEW_EVICT=false`). Idle TTL `PREVIEW_TTL_HOURS` (2), refreshed on try-it calls through the UI.
- [x] Reconciler on worker start and every 5 min: syncs DB rows with actual containers (by label), marks missing
      containers STOPPED, and removes orphan containers with no row.
- [x] Previews survive `docker compose restart`. After a full `make down`, previews are stopped (documented), and
      `make down-all` removes all `bga.*` containers, networks and images.

**Status (2026-10-26):** done. Verified on `make up`: stop/start through the API keeps the data; previews keep
running across `docker compose restart`; `make down` stops app + DB containers; after `make up` the reconciler
marks the row STOPPED ("container not running (exited)"); start brings it back on the same port. Notes:
- Action endpoints return 202 with the preview (`DELETE` → 202, empty body). `start` on a RUNNING preview is a
  no-op; start/restart/reset-db need a COMPLETED generation with `backend.zip` (409 otherwise).
- Eviction stops the least recently accessed preview (`last_accessed_at`). With `PREVIEW_EVICT=false` the API
  answers 409 `PREVIEW_LIMIT_REACHED`.
- Ports: a preview keeps its port while its row exists; when the range runs out, the least recently used
  stopped preview's app container is removed to free its port (image and data kept).
- TTL expiry runs every minute (reaper interval), reconciliation every `PREVIEW_RECONCILE_SECONDS` (300) and at
  worker start; a STARTING row older than build + health timeouts is marked FAILED ("start was interrupted").
- `make down-all` also removes `bga.sandbox` containers and networks.
