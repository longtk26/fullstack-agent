# Story 2.4 — Requirement → BackendSpec drafting

**Epic:** [2 — BackendSpec](epic2_backend_spec.md) · **Requirements:** FR-01, FR-07 (no invented policies) · **Depends on:** 2.3, 3.2

## User story

As a user without a ready-made spec, I want to describe my backend in plain language and get a valid
BackendSpec draft that I can review and edit, with every assumption the agent made listed explicitly.

## Acceptance criteria

- [ ] `POST /api/v1/spec-drafts` {mode: `requirement|frontend`, requirementText? | {baseSpec, siteJson}?, engine?} → 202 `{draftId}`.
      `mode=frontend` is the "Refine with AI" path from 2.5. Runs on the worker queue
      (not in the HTTP request). `GET /api/v1/spec-drafts/{id}` → `{status, backendSpec?, assumptions[],
      unresolved[], validation}`.
- [ ] The worker calls the selected `CodeEngine` in a scratch workspace with the `draft_spec` prompt (3.4),
      the JSON Schema, and the §5 example. The engine writes `spec.json` and `assumptions.json`.
- [ ] The output is validated with 2.2. If invalid, one automatic correction pass runs with the error list.
      If still invalid, it is returned as `status=NEEDS_REVIEW` with the errors attached. It does not hard-fail.
- [ ] Ambiguous critical policy (who can delete, state transitions, money rules) goes to `unresolved[]`.
      The model must not encode it as a rule (FR-07).
- [ ] The draft is never auto-submitted. The user explicitly submits the (edited) spec through 4.1.
- [ ] Progress for the draft job is visible (simple status polling is enough).

## Technical notes

- Reuses the engine adapter, so there is one credential path and Antigravity can draft too. The tool
  allowlist is file write in the scratch dir only.
