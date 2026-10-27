# Story 9.7a — Generate a frontend from the UI

**Epic:** [9 — Agent UI](epic9_agent_ui.md) · **Requirements:** FR-18, FR-21, FR-22 · **Depends on:** 9.2, 12.1, 12.2, 12.5, 13.5

## User story

As a user starting a new generation, I want to choose a static website or a dynamic web app, give its
FrontendSpec (and BackendSpec for a dynamic app), and generate it from the UI, then open the generated site.

> Split from 9.7 on 2026-10-27: this part makes frontend generation usable from the browser; the review aids
> (summary panel, contract preview, in-editor consistency markers, Requirement tab) are [9.7b](story9.7b_frontend_spec_review.md).

## What exists already

- API: `GET /api/v1/frontend-specs/schema`, `POST /api/v1/frontend-specs/validate` (consistency only with a saved
  `backendSpecId`), `POST /api/v1/generations` with `mode` + inline `frontendSpec` / `backendSpec`
  (422 `MODE_INPUT_MISMATCH` otherwise).
- UI: `NewGenerationView` with the BackendSpec flow (`JsonTab` / `JsonEditor` on Monaco, `use-json-editor`,
  `use-spec-validation`, `IssueList`, `SpecSummaryPanel`, `GenerationOptionsForm`, `spec-draft-store`); examples
  served at `/examples/index.json` (key `frontend-specs`, BackendSpecs under `specs`); the generation page already
  shows mode / lane badges, both lanes in the workflow, and **Open site** for the frontend preview.

## Acceptance criteria

- [ ] `/generations/new` starts with three mode cards — **Static website** ("pages only, no backend"), **Dynamic
      web app** ("frontend + backend from one API contract"), **Backend API only** (today's flow, unchanged). The
      choice is kept in the URL (`?mode=`) and the draft store; the default stays `backend`.
- [ ] Static: a **FrontendSpec** tab with the Monaco JSON editor bound to the FrontendSpec JSON Schema
      (autocomplete, inline markers), live validation through `/frontend-specs/validate` (debounced), the issue
      list jumping to the path, and **Load example** listing `frontend-specs` examples.
- [ ] Dynamic: a FrontendSpec editor and a BackendSpec editor (the existing JSON tab), each with live validation,
      plus the **consistency issues** between them in a list that names the editor to change (`path` in the
      FrontendSpec, `backendPath` in the BackendSpec) and jumps there. API: `POST /api/v1/frontend-specs/check-pair`
      with `{ frontendSpec, backendSpec }` inline (uses `check_spec_pair`), so unsaved editor text can be checked.
      Loading `project-tracker-dynamic` also offers to load its pair (`two-entity`); `shop-dynamic` → `shop`.
- [ ] Options form per mode (engine, repair limit, preview); submit sends `mode` + the spec(s) and is disabled
      while either spec or the consistency check has errors; the draft (mode + both texts) survives a reload.
- [ ] After submit the user lands on the generation page; on completion **Open site** opens the frontend preview
      (unchanged from 13.5).
- [ ] Closes the open 12.1 criterion (examples loadable in the UI).
- [ ] Verified in Docker (`make up`) with the fake engine: `static-landing` (static) and
      `project-tracker-dynamic` + `two-entity` (dynamic) created from the UI, completed, site opened.
- [ ] Lint, `tsc --noEmit`, and API tests for `check-pair` pass.
