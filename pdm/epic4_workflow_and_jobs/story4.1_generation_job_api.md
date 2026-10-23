# Story 4.1 — Generation job API & Redis queue

**Epic:** [4 — Workflow & jobs](epic4_workflow_and_jobs.md) · **Requirements:** FR-14, §7 · **Depends on:** 1.4, 2.3

## User story

As a client, I want to submit a BackendSpec and immediately get a job id, then poll its status, so that
generation never blocks my HTTP request.

## Acceptance criteria

- [ ] `POST /api/v1/generations` body `{backendSpec | specId, options}` → **202** `{generationId, status: "PENDING", createdAt}`.
  - Options (all optional): `maxRepairAttempts` (default 3, max 10), `runTests` (true), `generateDockerfile` (true),
    `deployPreview` (true), `engine` (`claude_code|antigravity|fake`), `timeoutSeconds`.
  - `deployPreview=true` with `generateDockerfile=false` → 422 `OPTIONS_CONFLICT`.
  - An invalid inline spec is still accepted (202) and fails at `validate_spec`. The UI pre-validates through 2.3.
- [ ] The job row is persisted, then `generationId` is pushed to the Redis list `bga:jobs`. If the push fails,
      the row stays PENDING and a startup sweeper re-enqueues PENDING rows older than 30 s.
- [ ] `GET /api/v1/generations/{id}` returns the §7 "completed" shape: `status`, `currentStep`, `repairAttempts`,
      `validation{syntax,lint,deps,startup,migration,conventions,tests,openapi}`, `artifacts{source,openapi,manifest,report}` (ids),
      `preview{status,url}`, `trace{langsmithUrl}`, timestamps, `error`.
- [ ] `GET /api/v1/generations?status=&cursor=` paginated list for the owner.
- [ ] Idempotency: an optional `Idempotency-Key` header returns the same job for repeated submits within 24 h.
