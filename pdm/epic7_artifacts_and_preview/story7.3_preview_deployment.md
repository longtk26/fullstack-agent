# Story 7.3 — Preview container deployment

**Epic:** [7 — Artifacts & preview](epic7_artifacts_and_preview.md) · **Requirements:** user requirement "generated backend runs as a separate container", FR-17 · **Depends on:** 7.1, 6.1 · **Open question:** Q6

## User story

As a client developer, I want every successfully generated backend to be running on its own container with a URL,
so that I can call it immediately from Postman, a frontend, or the UI's API explorer.

## Acceptance criteria

- [ ] Post-graph task `deploy_preview` (outside the generation status, so a preview failure doesn't make a
      COMPLETED generation FAILED) runs when `options.deployPreview=true`:
  1. `docker build` the generated Dockerfile → `bga-gen-<gen>:latest` (build timeout, build logs saved as an artifact).
  2. Create network `bga-previews-<gen>` and start `preview-db-<gen>`.
  3. Start `preview-<gen>` with env (`DB_URL`, random `JWT_SECRET`, `CORS_ORIGINS` = UI origin), resource
     limits, `restart: unless-stopped`, labels `bga.generation=<gen>`, and a free host port from `PREVIEW_PORT_RANGE`.
  4. The overlay entrypoint (5.2) runs `alembic upgrade head`. If the spec has `seed[]` (2.1/2.5), the worker mounts
     `seed.json` and the entrypoint loads it once into an empty DB (idempotent: skipped when the table has rows).
     The worker polls `/health` (60 s) → RUNNING, or FAILED with logs.
- [ ] `previews` row and `preview.status` events. `GET /api/v1/generations/{id}` includes
      `preview: {status, url: "http://localhost:<port>", openapiUrl, docsUrl}`.
- [ ] `GET /api/v1/generations/{id}/preview/logs?tail=200` (redacted).
- [ ] `GET /api/v1/generations/{id}/preview/requests?after=<cursor>`: structured request log of the backend
      preview (method, path, matched `operationId`, status, duration, timestamp), parsed from its access log, for
      the App tab's Network panel (9.9). Bodies are not recorded.
- [ ] Previews bind to `127.0.0.1` only by default (`PREVIEW_BIND_HOST`), because they are local-only and never exposed publicly.
