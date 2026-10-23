# Story 4.1 — Generation job API & Redis queue

**Epic:** [4 — Workflow & jobs](epic4_workflow_and_jobs.md) · **Requirements:** FR-14, §7 · **Depends on:** 1.4, 2.3

## User story

As a client, I want to submit a BackendSpec and immediately get a job id, then poll its status, so that
generation never blocks my HTTP request.

## Acceptance criteria

- [x] `POST /api/v1/generations` body `{backendSpec | specId, options}` → **202** `{generationId, status: "PENDING", createdAt}`.
  - Options (all optional, unknown keys rejected): `maxRepairAttempts` (default 3, 0–10), `runTests` (true), `generateDockerfile` (true),
    `deployPreview` (true), `engine` (`claude_code|antigravity|fake`, default `DEFAULT_ENGINE`), `timeoutSeconds` (60–7200).
  - `deployPreview=true` with `generateDockerfile=false` → 422 `OPTIONS_CONFLICT`.
  - An invalid inline spec is still accepted (202) and fails at `validate_spec`. The UI pre-validates through 2.3.
- [x] The job row is committed, then `generationId` is pushed to the Redis list `bga:jobs` (never before the commit). If the push fails,
      the row stays PENDING and a startup sweeper re-enqueues PENDING rows older than 30 s.
- [x] `GET /api/v1/generations/{id}` returns the §7 "completed" shape: `status`, `currentStep`, `repairAttempts`,
      `validation{syntax,lint,deps,startup,migration,conventions,tests,openapi}`, `artifacts{source,openapi,manifest,report}` (ids),
      `preview{status,url}`, `trace{langsmithUrl}`, timestamps, `error`.
- [x] `GET /api/v1/generations?status=&cursor=&limit=` paginated list for the owner (newest first, opaque cursor); `scope=all` for admins.
- [x] Idempotency: an optional `Idempotency-Key` header returns the same job for repeated submits within 24 h.
