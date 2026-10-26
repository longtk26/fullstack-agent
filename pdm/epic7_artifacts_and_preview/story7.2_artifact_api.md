# Story 7.2 — Artifact API

**Epic:** [7 — Artifacts & preview](epic7_artifacts_and_preview.md) · **Requirements:** FR-14, §7 (ids, not paths) · **Depends on:** 7.1

## User story

As a client, I want to list and download a job's artifacts by id, safely.

## Acceptance criteria

- [x] `GET /api/v1/generations/{id}/artifacts` → `[{artifactId, kind, name, size, sha256, contentType, createdAt}]`.
- [x] `GET /api/v1/generations/{id}/artifacts/{artifactId}` → streamed file with `Content-Disposition`. The path
      is resolved only from the DB row, never from user input. Owner-scoped (404 otherwise).
- [x] Failed jobs expose their diagnostic report, patches and logs as artifacts too.
- [x] `GET /api/v1/generations/{id}/files?path=` (read-only browse of the generated source for the UI, text files
      ≤ 1 MB, path traversal rejected). Optional; the UI falls back to the ZIP download.

**Status (2026-10-26):** done. The list is wrapped as `{items: [...]}` (like the other list endpoints), and
`GET /generations/{id}` now includes `artifacts[]` and `preview`. Files are served from `backend.zip`, not the
workspace (workspaces are deleted after 72 h): a directory returns `{type: "dir", entries}`, a text file
`{type: "file", content}`; binary or > 1 MB files → 409 `FILE_NOT_TEXT`; `..` → 400. Failed jobs get
`report.json/.md`, `repair-<n>.patch`, `validation-<n>.json` and `engine-logs.zip` (redacted on packaging; the
raw logs stay in the job's state directory). In Docker the artifacts live on the `artifacts` volume (worker
read-write, API read-only); host dev uses `.data/artifacts`.
