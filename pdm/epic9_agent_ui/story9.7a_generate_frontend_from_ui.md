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

- [x] `/generations/new` starts with three mode cards — **Static website** ("pages only, no backend"), **Dynamic
      web app** ("frontend + backend from one API contract"), **Backend API only** (today's flow, unchanged). The
      choice is kept in the URL (`?mode=`) and the draft store; the default stays `backend`.
- [x] Static: a **FrontendSpec** tab with the Monaco JSON editor bound to the FrontendSpec JSON Schema
      (autocomplete, inline markers), live validation through `/frontend-specs/validate` (debounced), the issue
      list jumping to the path, and **Load example** listing `frontend-specs` examples.
- [x] Dynamic: a FrontendSpec editor and a BackendSpec editor (the existing JSON tab), each with live validation,
      plus the **consistency issues** between them in a list that names the editor to change (`path` in the
      FrontendSpec, `backendPath` in the BackendSpec) and jumps there. API: `POST /api/v1/frontend-specs/check-pair`
      with `{ frontendSpec, backendSpec }` inline (uses `check_spec_pair`), so unsaved editor text can be checked.
      Loading `project-tracker-dynamic` also offers to load its pair (`two-entity`); `shop-dynamic` → `shop`.
- [x] Options form per mode (engine, repair limit, preview); submit sends `mode` + the spec(s) and is disabled
      while either spec or the consistency check has errors; the draft (mode + both texts) survives a reload.
- [x] After submit the user lands on the generation page; on completion **Open site** opens the frontend preview
      (unchanged from 13.5).
- [x] Closes the open 12.1 criterion (examples loadable in the UI).
- [x] Verified in Docker (`make up`) with the fake engine: `static-landing` (static) and
      `project-tracker-dynamic` + `two-entity` (dynamic) created from the UI, completed, site opened.
- [x] Lint, `tsc --noEmit`, and API tests for `check-pair` pass.

**Status (2026-10-27):** done. API: `POST /api/v1/frontend-specs/check-pair` (`CheckSpecPairUsecase`) returns only
the consistency issues plus `checked`; it is `false` (and nothing is compared) when either spec is invalid, or with a
warning when the FrontendSpec is static. UI: `ModeCards` + `useGenerationMode` (`?mode=` wins over the draft
store; the URL is updated with `history.replaceState`, the view sits in a `Suspense` boundary for
`useSearchParams`); `JsonTab` and `useSpecValidation` take a spec kind; `useSpecPairCheck` runs only once both
specs are server-valid (so it inherits their debounce); `ConsistencyIssueList` shows a `FrontendSpec · path` and
`BackendSpec · backendPath` link per issue; options are grouped per lane (`frontend` only sent for static/dynamic).
Deviations and additions:
- The example pairs (`project-tracker-dynamic` → `two-entity`, `shop-dynamic` → `shop`) are a UI constant
  (`EXAMPLE_PAIRS` in `features/specs/lib/spec-kinds.ts`), offered as a toast action in dynamic mode.
- A FrontendSpec whose `project.mode` does not match the chosen mode gets a client-side `MODE_INPUT_MISMATCH`
  error on `/project/mode` (the API would reject it), so submit stays disabled.
- Monaco's JSON schema settings are global; `JsonEditor` now keeps one schema association per model, so the two
  editors in dynamic mode no longer overwrite each other's schema.
- Fixed while verifying: syncing `?mode=` into the store before rehydration persisted an empty draft over the
  saved one; the sync now waits for `useSpecDraftHydrated()`.
- Consistency issues are listed, not yet marked inside the editors (9.7b).
Verified with `make up` and the fake engine, driving Chrome: `static-landing` (static) → `COMPLETED`, and
`project-tracker-dynamic` + `two-entity` (dynamic, loaded via the pair offer) → `COMPLETED_WITH_WARNINGS`
(integration skipped until Epic 14); both created from the UI, **Open site** served each site. Also checked:
mismatched pair (`shop-dynamic` + `two-entity`) lists 6 errors and disables submit, an issue link switches to the
BackendSpec tab, the mode and both texts survive a reload, and `?mode=static` selects the static card.
