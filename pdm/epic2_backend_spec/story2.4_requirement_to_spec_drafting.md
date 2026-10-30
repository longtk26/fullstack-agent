# Story 2.4 — Requirement → BackendSpec drafting

**Epic:** [2 — BackendSpec](epic2_backend_spec.md) · **Requirements:** FR-01, FR-07 (no invented policies) · **Depends on:** 2.3, 3.2

> **Status (2026-10-23): deferred.** Needs the Claude Code adapter (3.2) and the worker queue (4.1/4.2). Implement right after them; the `spec_drafts` table already exists (1.3).
>
> **Re-planned (2026-10-30):** first item after Epic 17's main stories, together with 12.4 and 9.7b. The draft
> endpoint serves all three generation modes, and the requirement can be a `.md` or `.txt` file.

## User story

As a user without a ready-made spec, I want to describe my backend in plain language, typed or as a Markdown / text
file, and get a valid BackendSpec draft that I can review and edit, with every assumption the agent made listed
explicitly.

## Acceptance criteria

- [x] `POST /api/v1/spec-drafts` {source: `requirement|frontend`, mode: `backend|static|dynamic`, requirementText?,
      requirementFormat?: `text|markdown`, requirementFileName?, {baseSpec, siteJson}?, engine?} → 202 `{draftId}`.
      `source=frontend` is the "Refine with AI" path from 2.5. `mode=backend` drafts a BackendSpec (this story);
      `static` / `dynamic` are 12.4. Runs on the worker queue (not in the HTTP request).
      `GET /api/v1/spec-drafts/{id}` → `{status, mode, backendSpec?, frontendSpec?, assumptions[], unresolved[],
      validation}`.
- [x] **Requirement input:** plain text or Markdown, typed or uploaded as a `.md` / `.txt` / `.markdown` file. UTF-8
      only, up to 64 KB; other file types (PDF, DOCX, images) and binary content are rejected with a clear error.
      The original text and file name are stored with the draft and saved as `requirement.md` (or `.txt`) in the
      generation's artifacts when the draft is submitted.
- [x] The worker calls the selected `CodeEngine` in a scratch workspace with the `draft_spec` prompt (3.4),
      the JSON Schema, and the §5 example. The engine writes `spec.json` and `assumptions.json`.
- [x] The output is validated with 2.2. If invalid, one automatic correction pass runs with the error list.
      If still invalid, it is returned as `status=NEEDS_REVIEW` with the errors attached. It does not hard-fail.
- [x] Ambiguous critical policy (who can delete, state transitions, money rules) goes to `unresolved[]`.
      The model must not encode it as a rule (FR-07).
- [x] Entities and CRUD operations are drafted so the backend CRUD templates (17.6) apply; anything else is listed
      in `assumptions[]` as needing the engine.
- [x] The draft is never auto-submitted. The user explicitly submits the (edited) spec through 4.1.
- [x] Progress for the draft job is visible (simple status polling is enough). Draft jobs are counted in usage
      (8.4).
- [x] The fake engine has a draft fixture per mode (listed in `docs/development/test-doubles.md`).

## Technical notes

- Reuses the engine adapter, so there is one credential path and Antigravity can draft too. The tool
  allowlist is file write in the scratch dir only.
- The UI reads an uploaded file in the browser and sends its text; the API checks size, encoding and extension
  again.

**Status (2026-10-30):** done on `feat/story2.4-requirement-drafting`, together with 12.4 (one draft runner for all
three modes). Verified with tests (`tests/test_drafting.py`) and on `make up` with the fake engine (all three
`examples/requirements/*.md` draft in 0.5–1.6 s; a static generation from a draft carries `requirement.md`).
Deviations and notes:
- Files: the engine writes `backend-spec.json` / `frontend-spec.json` and one `notes.json`
  (`{assumptions, unresolved}`, each `{spec?, path, message}`) instead of `spec.json` + `assumptions.json`.
  Prompts `draft_spec@v2` (v1 kept), `draft_frontend_spec@v1`, `repair_spec@v1`; conventions in `draft_conventions.md`.
- Drafts have their own Redis queue (`bga:drafts:<engine>`), worker slots (`DRAFT_CONCURRENCY=2`) and scratch
  directory (`<WORKSPACE_ROOT>/drafts/<id>`, removed afterwards). They are claimed in the DB (PENDING → RUNNING); a
  draft whose worker stops is failed by the reaper (`DRAFT_STALE_SECONDS`), one no worker picks up within
  `DRAFT_PENDING_TIMEOUT_SECONDS` too. They are not resumed: drafting again is cheap.
- The worker gets the repo's `examples/` (`EXAMPLES_DIR`, a build context in compose) for the engine's reference
  specs and the fake engine's draft fixtures.
- Drafted specs are stored as `json`, not `jsonb`, so the editor shows the engine's key order.
- `POST /generations` takes `draftId`: the specs are stored with `source=requirement` and the requirement text, and
  packaging writes `requirement.md` / `requirement.txt`.
- "Refine with AI" (`source=frontend`) works in the API and the runner; its button in the Import tab (9.2) is still
  disabled.
- Not verified with a paid engine (CLAUDE.md: fake engine only unless asked): whether real engines keep policy out of
  the spec and prefer CRUD is down to the prompt.
