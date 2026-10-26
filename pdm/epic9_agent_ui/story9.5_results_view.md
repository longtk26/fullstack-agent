# Story 9.5 — Results: validation, artifacts & source

**Epic:** [9 — Agent UI](epic9_agent_ui.md) · **Requirements:** FR-11, FR-16, FR-17 · **Depends on:** 9.3, 7.2

## User story

As a user, I want to see exactly which checks passed and download or browse what was generated.

## Acceptance criteria

- [x] Validation table: each of the 8 checks (including `conventions`, whose rows link the violated skill rule) with status (passed / failed / skipped / not run), duration and
      attempt history (e.g. `tests: failed → passed (repair #1)`). Expanding a row shows the failure summary.
- [x] Artifacts list with download buttons (ZIP, openapi.json, manifest.json, report, patches, logs).
- [x] Manifest viewer: modules, operations table, auth requirements, env vars, frontend bindings (if imported), and unresolved items highlighted.
- [x] Source browser: file tree + read-only code viewer with syntax highlighting (7.2 files API).
- [x] FAILED jobs show the diagnostic report rendered as markdown.

**Status (2026-10-26):** done; verified in the browser against `make up` (completed and failed fake runs).
- New endpoint `GET /generations/{id}/validation`: every check per attempt (status, duration, summary, findings,
  output tail). The Results tab shows the latest result, the history (`failed → passed (1 repair)`) and, when a
  row is expanded, each attempt's findings with the violated skill rule.
- Downloads are plain links through the BFF proxy (`/api/proxy/...`, which now forwards `content-disposition`).
- The manifest viewer shows modules, operations (method, path, operationId, auth, request → response, status
  codes, bound frontend components), env vars (required / secret) and unresolved items or contract problems.
- The source browser lists `backend.zip` lazily (one request per opened folder) and shows files read-only in
  Monaco with syntax highlighting.
- FAILED: `report.md` rendered with react-markdown + remark-gfm; the failure banner links to it.
