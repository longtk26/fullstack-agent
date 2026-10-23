# Story 7.2 — Artifact API

**Epic:** [7 — Artifacts & preview](epic7_artifacts_and_preview.md) · **Requirements:** FR-14, §7 (ids, not paths) · **Depends on:** 7.1

## User story

As a client, I want to list and download a job's artifacts by id, safely.

## Acceptance criteria

- [ ] `GET /api/v1/generations/{id}/artifacts` → `[{artifactId, kind, name, size, sha256, contentType, createdAt}]`.
- [ ] `GET /api/v1/generations/{id}/artifacts/{artifactId}` → streamed file with `Content-Disposition`. The path
      is resolved only from the DB row, never from user input. Owner-scoped (404 otherwise).
- [ ] Failed jobs expose their diagnostic report, patches and logs as artifacts too.
- [ ] `GET /api/v1/generations/{id}/files?path=` (read-only browse of the generated source for the UI, text files
      ≤ 1 MB, path traversal rejected). Optional; the UI falls back to the ZIP download.
