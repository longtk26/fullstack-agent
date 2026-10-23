# Story 9.5 — Results: validation, artifacts & source

**Epic:** [9 — Agent UI](epic9_agent_ui.md) · **Requirements:** FR-11, FR-16, FR-17 · **Depends on:** 9.3, 7.2

## User story

As a user, I want to see exactly which checks passed and download or browse what was generated.

## Acceptance criteria

- [ ] Validation table: each of the 8 checks (including `conventions`, whose rows link the violated skill rule) with status (passed / failed / skipped / not run), duration and
      attempt history (e.g. `tests: failed → passed (repair #1)`). Expanding a row shows the failure summary.
- [ ] Artifacts list with download buttons (ZIP, openapi.json, manifest.json, report, patches, logs).
- [ ] Manifest viewer: modules, operations table, auth requirements, env vars, frontend bindings (if imported), and unresolved items highlighted.
- [ ] Source browser: file tree + read-only code viewer with syntax highlighting (7.2 files API).
- [ ] FAILED jobs show the diagnostic report rendered as markdown.
