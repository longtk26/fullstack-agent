# Story 9.6 — OpenAPI explorer & try-it against preview

**Epic:** [9 — Agent UI](epic9_agent_ui.md) · **Requirements:** user requirement (visualize OpenAPI + test calls), FR-17 · **Depends on:** 9.5, 7.3

## User story

As a user, I want to browse the generated API and fire real requests at the running backend container, so that I
can check behaviour right after generation.

## Acceptance criteria

- [x] API tab renders the job's `openapi.json` artifact with Scalar: endpoints grouped by tag, schemas, and
      `operationId` visible on each operation.
- [x] A preview control bar shows status (STARTING/RUNNING/STOPPED/FAILED), URL (copy), start/stop/restart/reset-DB,
      expiry countdown, and a logs drawer (7.3 / 7.4).
- [x] Try-it uses the preview URL as the server. Requests go browser → preview directly (CORS is allowed by
      `CORS_ORIGINS`). When the preview isn't RUNNING, try-it is disabled with a "Start preview" call-to-action.
- [ ] *(deferred to Epic 10: generated backends have no auth yet)* Auth helper when the spec has JWT auth: a "Get token" form calls the generated register/login operations and
      injects `Bearer` into Scalar's auth. The token is kept in memory only (not persisted).
- [x] Each try-it call pings `POST /generations/{id}/preview/touch` (debounced) to extend the TTL.
- [x] Without a preview (`deployPreview=false`), the docs still render read-only.
- [x] For imported specs, each operation shows the frontend components bound to it (from the manifest `frontendBindings`).
      Seeded previews return the site's real records immediately (e.g. `GET /posts?sort=-date&limit=4`).

**Status (2026-10-26):** done except the auth helper (needs Epic 10). Verified in the browser: Scalar
(`@scalar/api-reference-react` 0.9.80) renders the job's `openapi.json` with operationIds; the server is the
preview URL; try-it sent `GET /health` (200) and `POST /projects` (422 error envelope) straight from the browser
to the preview; the request log showed the call with `project.create`; `touch` refreshed the TTL.
- Scalar runs **local-only**: telemetry, hosted fonts, the AI agent and developer tools are switched off, and the
  "Generate SDK" button (which uploads the document to Scalar) is hidden with `customCss` because it has no
  switch. The browser made no request to any non-local host during the check.
- Try-it is disabled (read-only reference) unless the preview is RUNNING; the control bar shows status, URL
  (copy, open Swagger UI), idle countdown, start / stop / restart / reset-DB (confirm dialog) and a drawer with
  the request log and container logs (polled every 3 s while open).
- Touch is debounced to once a minute.
- Frontend bindings (imported site JSON) are appended to each operation's description in the explorer and shown
  as a column in the manifest viewer (9.5).
- The request log skips CORS preflights (`OPTIONS`) and `/health`.
