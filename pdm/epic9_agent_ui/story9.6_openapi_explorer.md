# Story 9.6 — OpenAPI explorer & try-it against preview

**Epic:** [9 — Agent UI](epic9_agent_ui.md) · **Requirements:** user requirement (visualize OpenAPI + test calls), FR-17 · **Depends on:** 9.5, 7.3

## User story

As a user, I want to browse the generated API and fire real requests at the running backend container, so that I
can check behaviour right after generation.

## Acceptance criteria

- [ ] API tab renders the job's `openapi.json` artifact with Scalar: endpoints grouped by tag, schemas, and
      `operationId` visible on each operation.
- [ ] A preview control bar shows status (STARTING/RUNNING/STOPPED/FAILED), URL (copy), start/stop/restart/reset-DB,
      expiry countdown, and a logs drawer (7.3 / 7.4).
- [ ] Try-it uses the preview URL as the server. Requests go browser → preview directly (CORS is allowed by
      `CORS_ORIGINS`). When the preview isn't RUNNING, try-it is disabled with a "Start preview" call-to-action.
- [ ] Auth helper when the spec has JWT auth: a "Get token" form calls the generated register/login operations and
      injects `Bearer` into Scalar's auth. The token is kept in memory only (not persisted).
- [ ] Each try-it call pings `POST /generations/{id}/preview/touch` (debounced) to extend the TTL.
- [ ] Without a preview (`deployPreview=false`), the docs still render read-only.
- [ ] For imported specs, each operation shows the frontend components bound to it (from the manifest `frontendBindings`).
      Seeded previews return the site's real records immediately (e.g. `GET /posts?sort=-date&limit=4`).
