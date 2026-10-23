# Story 7.4 — Preview lifecycle management

**Epic:** [7 — Artifacts & preview](epic7_artifacts_and_preview.md) · **Depends on:** 7.3 · **Open question:** Q6

## User story

As the operator, I want to start, stop and clean up preview containers, so that my machine doesn't fill up with
old backends.

## Acceptance criteria

- [ ] `POST /api/v1/generations/{id}/preview/start | stop | restart`, `DELETE /api/v1/generations/{id}/preview`
      (removes the container, DB volume and image). `POST .../preview/reset-db` drops and recreates the preview DB.
- [ ] `GET /api/v1/previews` lists the owner's previews with status, port and expiry.
- [ ] `POST /api/v1/generations/{id}/preview/touch` refreshes `last_accessed_at` and extends the expiry (called by the UI try-it, 9.6).
- [ ] Limits: `PREVIEW_MAX_RUNNING` (3). Starting another stops the least recently used one (or 409 when
      `PREVIEW_EVICT=false`). Idle TTL `PREVIEW_TTL_HOURS` (2), refreshed on try-it calls through the UI.
- [ ] Reconciler on worker start and every 5 min: syncs DB rows with actual containers (by label), marks missing
      containers STOPPED, and removes orphan containers with no row.
- [ ] Previews survive `docker compose restart`. After a full `make down`, previews are stopped (documented), and
      `make down-all` removes all `bga.*` containers, networks and images.
