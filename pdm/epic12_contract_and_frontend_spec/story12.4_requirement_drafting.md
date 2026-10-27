# Story 12.4 — Requirement → FrontendSpec (+ BackendSpec) drafting

**Epic:** [12 — Modes, FrontendSpec & contract](epic12_contract_and_frontend_spec.md) · **Requirements:** FR-24, FR-01 · **Depends on:** 12.1, 2.4, 3.2

## User story

As a user, I want to describe my site in plain language and get a FrontendSpec (and, for a dynamic app, the
matching BackendSpec) that I can review, instead of writing JSON.

## Acceptance criteria

- [ ] Draft job (same infrastructure as 2.4, purpose `draft_frontend_spec`): requirement + mode → the engine
      writes `frontend-spec.json` and, in `dynamic` mode, `backend-spec.json`. Both are validated (12.1, 2.2) and
      repaired by the engine up to 2 times; the result lists **assumptions** (e.g. "added a contact page") and
      **unresolved** questions the user must acknowledge.
- [ ] The drafter decides the page list from the requirement (every user-visible feature maps to at least one
      page or section) and picks a theme preset and colours from any brand words in the requirement.
- [ ] In `dynamic` mode the BackendSpec is derived from the FrontendSpec's data needs (every `operationId` used
      by a page or form exists as an operation), reusing the deterministic rules of 2.5 where possible.
- [ ] `static` mode never produces a BackendSpec or bindings; data shown on pages goes into `content`.
- [ ] Prompt versions and outputs are stored; the draft can be edited in the UI (9.7b) before generation.
