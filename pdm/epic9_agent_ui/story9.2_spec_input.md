# Story 9.2 — Spec input: requirement, frontend import & JSON

**Epic:** [9 — Agent UI](epic9_agent_ui.md) · **Requirements:** FR-01, FR-02 · **Depends on:** 9.1, 2.3, 2.4

## User story

As a user, I want to start from a plain-language requirement, an existing frontend site JSON, or BackendSpec JSON,
see validation errors while I type, and only submit when the spec is valid.

## Acceptance criteria

- [ ] `/generations/new` with three tabs:
  - **Requirement**: textarea (with example prompts), engine select, "Draft spec" → draft job progress → the
    resulting spec opens in the JSON tab, with **Assumptions** and **Unresolved** panels the user must acknowledge.
  - **Import frontend JSON** (decision Q5): drop or upload a site JSON (or "Load sample" → `revue-de-mode.json`), and toggle
    "Include admin CRUD". Calls 2.5 and shows a preview before switching to the JSON tab:
    - **Generated example BackendSpec** (read-only Monaco, with "Edit in JSON tab" and "Download .json")
    - **Bindings** table: page → component → operationId, so it is visible which UI element drives which endpoint
    - **Seed data** table: the first rows per entity, with a count
    - **Assumptions** / **Unresolved** panels, plus a "Refine with AI" button (2.4 `mode=frontend`, shows a diff against the deterministic draft)
  - **JSON**: Monaco editor bound to the BackendSpec JSON Schema (autocomplete, hover docs). Toolbar: Load example
    (from `examples/specs`), Upload `.json`, Format, Download.
- [ ] Live validation: debounced (500 ms) `POST /specs/validate`. Issues are shown as Monaco markers (JSON pointer →
      range) and in a clickable error list that jumps to the line.
- [ ] Summary side panel parsed from the current JSON: entities (fields and relationship count) and operations
      table (method, path, operationId), so the user can sanity-check before generating.
- [ ] Options form (RHF + Zod): engine, maxRepairAttempts (1–10), runTests, generateDockerfile, deployPreview.
      The conflict rule from 4.1 is mirrored in Zod.
- [ ] Submit is disabled while errors exist → `POST /generations` → redirect to `/generations/[id]`.
- [ ] Unsaved editor content is kept as a per-browser draft (Zustand persist with `partialize`, spec text only, no tokens).
