# Story 7.3 — Preview container deployment

**Epic:** [7 — Artifacts & preview](epic7_artifacts_and_preview.md) · **Requirements:** user requirement "generated backend runs as a separate container", FR-17 · **Depends on:** 7.1, 6.1 · **Decision:** Q6 (auto-start, 2 h TTL, max 3, 18000–18099, 127.0.0.1)

## User story

As a client developer, I want every successfully generated backend to be running on its own container with a URL,
so that I can call it immediately from Postman, a frontend, or the UI's API explorer.

## Acceptance criteria

- [x] Post-graph task `deploy_preview` (outside the generation status, so a preview failure doesn't make a
      COMPLETED generation FAILED) runs when `options.deployPreview=true`:
  1. `docker build` the generated Dockerfile → `bga-gen-<gen>:latest` (build timeout, build logs saved as an artifact).
  2. Create network `bga-previews-<gen>` and start `preview-db-<gen>`.
  3. Start `preview-<gen>` with env (`DB_URL`, random `JWT_SECRET`, `CORS_ORIGINS` = UI origin), resource
     limits, `restart: unless-stopped`, labels `bga.generation=<gen>`, and a free host port from `PREVIEW_PORT_RANGE`.
  4. The overlay entrypoint (5.2) runs `alembic upgrade head`. If the spec has `seed[]` (2.1/2.5), the worker mounts
     `seed.json` and the entrypoint loads it once into an empty DB (idempotent: skipped when the table has rows).
     The worker polls `/health` (60 s) → RUNNING, or FAILED with logs.
- [x] `previews` row and `preview.status` events. `GET /api/v1/generations/{id}` includes
      `preview: {status, url: "http://localhost:<port>", openapiUrl, docsUrl}`.
- [x] `GET /api/v1/generations/{id}/preview/logs?tail=200` (redacted).
- [x] `GET /api/v1/generations/{id}/preview/requests?after=<cursor>`: structured request log of the backend
      preview (method, path, matched `operationId`, status, duration, timestamp), parsed from its access log, for
      the App tab's Network panel (9.9). Bodies are not recorded.
- [x] Previews bind to `127.0.0.1` only by default (`PREVIEW_BIND_HOST`), because they are local-only and never exposed publicly.

**Status (2026-10-26):** done and verified on `make up` (fake engine): COMPLETED → preview RUNNING on
`127.0.0.1:18000` in ~100 s (image build included), seed row present, full CRUD round trip, request log with
operationIds, CORS for the UI origin. Design notes and deviations:
- **The worker owns Docker; the API does not get the socket.** Preview actions go from the API to the worker over
  Redis (`PreviewCommandBus`: fire-and-forget for start/stop/…, request/reply for logs and the request log; 503
  `WORKER_UNAVAILABLE` when no worker answers within 8 s).
- The image is built from **`backend.zip`** (not the workspace), so previews can be rebuilt after workspace
  cleanup and every preview proves the ZIP builds and starts on its own. The build log is saved as the
  `preview-build.log` artifact (also on failure).
- Names: `bga-preview-<gen>` (app), `bga-preview-db-<gen>` + volume, network `bga-preview-net-<gen>`, image
  `bga-gen-<gen>:latest`. Labels `bga.preview`, `bga.instance`, `bga.role`. The network is a normal bridge
  (Docker publishes ports only from non-internal networks), so preview apps have outbound network access.
- DB password and `JWT_SECRET` are derived from the agent `JWT_SECRET` + generation id (HMAC): stable across
  restarts, unique per preview, never stored, and redacted from preview logs.
- Health is probed inside the container (`exec` + urllib), so the check works whether the worker runs in
  Docker or on the host. The app container drops all capabilities.
- `seed.json` is copied into the container (`put_archive`) instead of a bind mount (no host-path coupling).
- Request log: JSON access-log lines from the generated app (overlay middleware), parsed from `docker logs`;
  `cursor` = timestamp of the last entry.
