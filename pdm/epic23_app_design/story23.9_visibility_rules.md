# Story 23.9 — Visibility rules (backend)

**Epic:** [23 — App design](epic23_app_design.md) · **Requirements:** FR-06, FR-07, FR-34 · **Depends on:** Epic 10

Backend and contract only. It can start at any time, in parallel with Checkpoints A–C.

## User story

As a user drafting an app, I want a requirement that hides records from some roles (for example "only published
items are shown to customers") to become a backend rule, so that those roles can't reach the hidden records by
calling the API, whatever the frontend shows.

## Context

- The policies plugin (10.3) has role policies (`require_roles`), ownership (`repository_filters`: `owned_by`,
  `bypassRoles`) and per-record `allowedActions`. It has no rule that hides records by their values.
- Areas (23.10) show different products to different roles. Without this rule an area would have to filter in the
  browser, which decision D7 forbids.

## Steps

1. **BackendSpec.** A `policies` entry of kind `visibility`: `{entity, roles, where}`, where `where` is equality on
   the entity's fields (`{"status": "PUBLISHED"}`), optionally `{"or": "owner"}` to also show the user's own records.
   Roles not listed see everything (subject to their other policies). Validated: fields exist, values fit their
   types, roles exist in `auth.roles`.
2. **Backend (plugin code).** The rule joins `repository_filters`: lists, `get` (a hidden record is 404, as for
   ownership), child lists through a hidden parent, and aggregates (a learner's dashboard counts only what they may
   see). Guests (no token) count as the rule's public case when the entity has public reads.
3. **Contract.** `x-bga.visibility` on the affected operations (roles and the condition, for the frontend to explain
   empty lists, never to filter); a scenario per rule: a hidden record is absent from the list and 404 on `get` for
   the role, present for the others.
4. **Mocks.** `src/mocks/plugins.ts` applies the same rule from `plugins.json`; the scenarios pass on MSW and live.
5. **Drafting.** `draft_app` (next version, with 23.6's) learns the rule: sentences like "only see published",
   "only active members are listed" become `visibility` policies, not frontend filters. The answer schema types it.
6. Tests: template tests for list, get, child lists and aggregates per role; contract and scenarios; MSW emulation;
   validator errors; a recorded LMS draft that drafts the rule.

## Acceptance criteria

- [ ] In the LMS app a learner's course list and course count exclude drafts, a draft's `get` is 404, and a manager
      sees every course, live and on MSW.
- [ ] The rule's scenarios run in the smoke check and on MSW and pass.
- [x] A rule naming an unknown field, value or role is refused with a clear error.
- [x] Existing ownership and role policies behave exactly as before (their template tests unchanged).

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test` (template tests), `make up` with the LMS golden app, live
calls as learner and manager.

## Status

**Implemented (2026-11-06); the live and smoke runs wait for the user's real test.**
- **BackendSpec:** `policies[]` of type `visibility` (`entity`, `roles`, `where`), validated (entity, fields, enum
  values, roles; naming it on an operation is an error: it applies by itself).
- **Policies plugin:** list and get carry the rule; a restricted or signed-out caller's list narrows
  (`visible_only` repository filter) and a hidden record is 404; public reads take the signed-in user if any; template
  tests `hidden_record` and `visible_only`; the contract's `x-bga.visibility` (operation and entity) and a 404 scenario
  for a restricted demo user; scenarios reading a hidden record run as a user who may see it. The mocks apply it.
- **Figures:** the unguarded aggregates of such an entity get a role policy for the other roles (Story 23.0's revenue
  leak). Found doing it: **the planner ignored every policy on an aggregate** (Epic 21); fixed, and an aggregate route
  now takes the plugins' guards (`require_roles`).
- `draft_app@v3` asks for the rule; the kit explains a narrowed empty list ("Only published courses are shown to
  you"), never filters.
- Verified: `tests/test_visibility_rules.py` (on Learnly with the rule its requirement implies) and the full suite.

Deviations: a child list through a hidden parent is not narrowed (only the entity's own lists and reads).
