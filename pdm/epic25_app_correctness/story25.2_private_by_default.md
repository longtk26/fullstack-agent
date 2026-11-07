# Story 25.2 — Private by default: records tied to a person

**Epic:** [25 — App correctness](epic25_app_correctness.md) · **Requirements:** FR-39 · **Depends on:** 10.3, 23.9

## User story

As a business owner trying the POC, I want every user to see only the records that are theirs (and staff roles to see
what their work needs), without having to spell it out in the requirement.

## Context

- F1 in 3 / 3 apps: other users of the same role read records that are not theirs (`GET …/{id}` → 200), even when the
  requirement says in plain words that people see only their own records.
- The policies plugin (10.3) has ownership (`ownerField`, `bypassRoles`, deny 404) and 23.9 has visibility rules; the
  drafts did not use them on these records, or used them only on some operations (ownership on get and one action,
  none on list).

## Steps

1. **Find the person reference.** In code, after the draft (with `fix_backend_defaults`): an entity is *tied to a
   person* when it references the signed-in user's entity (any field whose target is the auth user entity, whatever
   the draft named it), directly or through a parent that is (a child of a person-tied parent follows the parent).
2. **Default policy.** Unless the requirement or the draft marks the entity public: ownership on get, list, update,
   delete and the entity's custom operations for the person's role, with bypass for the staff roles the outline's
   areas give that entity (back-office roles); lists narrow to the person's records. A record reached through a parent
   follows the parent's owner.
3. **Assigned workers.** A second reference to the user entity whose role is a worker role (an assignee) also grants
   that worker read access once assigned, and only then (the lab saw workers read records before assignment).
4. **Draft prompt.** `draft_app` learns the rule in one paragraph and one example; code still adds what the draft left
   out, with a note in the draft's assumptions ("<Entity> records are private to their <role>").
5. **Contract, mocks, scenarios** carry the policies as today (10.3, 23.9); the contract gains scenarios
   "another <role> → 404" per private entity, run by the frontend's `scenarios` check and the backend smoke check.
6. Tests on synthetic specs covering the shapes, not one domain: direct owner, owner through a parent, an assignee,
   no person reference (a catalogue); policies added; the golden apps' public records stay public.

## Acceptance criteria

- [ ] For every person-tied entity, another user of the same role gets 404 on get and does not see the record in
      lists, on mocks and live.
- [x] Staff roles still see what their area needs; an assigned worker sees a record only once assigned to them.
- [x] Records with no person reference (reference data, catalogues) are unchanged; the static and app golden tests
      pass.

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test`, the lab set re-checked in 25.6.

## Status

Criteria marked open need the live apps: they are checked by the real generations of 26.7.

**Done 2026-11-07.** `drafting/access.py` (`secure_access`, run in the app draft after the BackendSpec is valid and
only when it stays valid, `drafting/app.apply_access_rules`): the person-tied entities are found from the draft's
ownership policies or a field named after a role (`<role>Id`, `<role>UserId`); reads, edits and record actions without
a policy get the owner's policy (staff bypass), figures over private records become the staff's, and every change is a
note in the draft's assumptions. `draft_app@v4` explains the rule in one paragraph. Tests on synthetic specs:
`tests/test_access_rules.py`. Planned offline on the three lab drafts: valid BackendSpec, valid FrontendSpec, no pair
issue, nothing uncovered.

Deviations: a record reached only through a parent (a child of a person-tied parent) is not made private by itself
(no draft in the lab needed it; the draft prompt asks for it). An assigned worker opens a record by its id (the
worker's role bypasses the read) but does not get a list limited to assigned records; their own list is the draft's
custom operation. The re-check is 26.7's (25.6).
