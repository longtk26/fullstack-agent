# Story 25.1 — Pipeline fixes: dashboard cap, unique fields in the mock, the draft check matches the generation's

**Epic:** [25 — App correctness](epic25_app_correctness.md) · **Requirements:** FR-36 · **Depends on:** Epic 22

## User story

As a user, I want a draft the drafting accepts to always generate, and the generated mocks to agree with the contract,
so a run never stops on the generator's own mistakes.

## Context (lab, 2026-11-07: F5, F6)

- F5: `frontend/app/outline.py` caps the outline's dashboard at `MAX_DASHBOARD` (6); `frontend/app/screens.py`
  `ensure_aggregates` then appends every aggregate no dashboard item names ("coverage by construction") without the cap.
  The drafting's check passed (NEEDS_REVIEW); the generation's `validate_inputs` refused it.
- F6: the contract writes one `CONFLICT` error per operation with every unique column (`fields: ["<a>", "<b>"]`);
  `templates/nextjs_overlay/files/dynamic/src/mocks/plugins.ts` refuses only when **all** listed fields match
  (`fields.every`). `uniqueTogether` has its own rule above it.

## Steps

1. **Dashboard:** `ensure_aggregates` keeps the named items first, then adds unnamed aggregates while there is room;
   an aggregate that does not fit is removed from the BackendSpec with a note (it has no screen), so coverage holds.
2. **Unique fields:** separately unique columns are "any one of these": the mock checks each field on its own (`some`)
   and answers with that field in `details.fields`; or the contract emits one `CONFLICT` per unique column (choose the
   one that keeps the frontend's 409 handling in `errors.ts` unchanged and record it).
3. **One check for both:** the draft check (`check_draft` for dynamic drafts) runs the same input validation as the
   generation's `validate_inputs` (schema limits included), so such a draft ends the draft as invalid with the reason,
   and a repair round can fix it.
4. Tests: an outline with 6 named figures plus 2 unnamed aggregates; an entity with two unique columns (scenarios on the
   mocks: duplicate name → 409, duplicate code → 409, both new → 201); a draft over a schema limit fails the draft check.

## Acceptance criteria

- [x] No dashboard exceeds 6 items; every aggregate in the BackendSpec is on a screen.
- [ ] The mocks answer 409 for each separately unique field, as the backend does; `frontend:scenarios` passes for
      any entity with more than one unique field (the lab draft that showed it is kept as a regression fixture).
- [x] A draft the generation would refuse is refused by the draft check, with the same message.

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test` (mocks), and the lab draft that showed F5 and F6
(`lab/business-value/runs/buyright-1`) on the fake engine as a regression fixture.

## Status

Partly checked 2026-11-07 (26.7): `frontend:scenarios` passed with the mock change on both HomeFix generations (85 and 86 scenarios), but neither has an entity with more than one unique field, so the criterion itself is still unexercised (left open).

**Done 2026-11-07.** `ensure_aggregates` fills the dashboard while there is room and drops an aggregate that has no
screen from the BackendSpec (and from the drafted file, `drafting/app.py`), with a note; the mock checks each
separately unique field on its own (`mocks/plugins.ts`) and answers 409 with that field. Tests:
`test_app_screens.py::test_the_dashboard_never_passes_its_cap_and_every_aggregate_has_a_screen`, the mock assertion in
`test_app_plugins.py`.

Step 3 needed no change: the app draft's final check already validates the planned FrontendSpec (the lab's draft
ended NEEDS_REVIEW with exactly this error; the lab submitted it anyway). Two more pipeline crashes, found by the real
`agy` drafts of this epic, were fixed here: `"pagination": true` on a custom list (the normalizer expanded it only for
CRUD lists; the contract crashed) and a custom paginated list without a planned list DTO
(`test_access_rules.py::test_pagination_true_on_a_custom_list_means_the_default_limits`). The sandbox scenarios for
the mock were not run (the user's limit on slow tests); the real generations of 26.7 run them.

**Found in 26.7 (2026-11-07): two keys to the same model.** Both HomeFix generations failed the backend smoke check:
login and register answered 500 because a repair request has two keys to users (the tenant who reported it, the
contractor assigned to it) and the planner named both relationships `user`, both back-populating `repair_requests`,
so SQLAlchemy could not map the user model (`AmbiguousForeignKeysError`). Epic 25's person fields (an owner and an
assigned worker) make this common. `backend/planner.py` now names each relationship of such a pair after its key
(`reporter` / `tickets_as_reporter`) and `codegen.model_file` adds `foreign_keys`; a pair linked once is generated
as before. Test: `tests/test_two_keys_to_one_model.py` (the generated models configure in SQLAlchemy).

**Also found in 26.7 (2026-11-07): an update without the file field.** With the relationships fixed, HomeFix's
`PATCH /repair-requests/{id}` still answered 500: the update body leaves the photo out (only the tenant sets it when
reporting), but the storage plugin's upload check read `dto.photo` (`AttributeError`). The plugin took every writable
column instead of the body's own fields. The planner now keeps an operation's `request.fields` on the planned
operation (`requestFields`) and the plugin checks only those. Test:
`test_storage.py::test_an_update_that_leaves_the_file_out_checks_no_upload`.

**Found in 26.7 (2026-11-08): custom operations without a response type.** HomeFix's contractor operations
(`GET /repair-requests/assigned-jobs`, `GET /repair-requests/jobs/{id}`, and the record actions) named their entity but
no response; the contract had no type, the backend answered `{"ok": true}` and the contractor's page showed "Ok: Yes"
instead of their jobs. `drafting/app.fix_backend_defaults` now gives such an operation its entity's response (a record
for `GET …/{id}` and record actions, a list for another `GET`), with a note. Test:
`test_structured_drafts.py::test_a_custom_operation_of_an_entity_answers_with_its_records`.

**Found in 26.7 (2026-11-08): the contract's scenarios contradicted each other.** A real draft (volunteer shifts)
failed `frontend:scenarios` 5 times; the mocks were right, the scenarios were not (the backend's smoke check passes
any 4xx, so it never noticed): `_fresh` made "Scenario <id>" for a unique id (a unique reference then pointed nowhere);
the one-to-one plugin moved only the success onto a free parent and its "second …" scenario had no user (the
coordinator-only create answered 403); the uniqueTogether plugin moved only the success onto a free pair (a unique
field's duplicate then hit two conflicts); and with every seeded record locked (`immutableAfter` on the only status)
an update success was still expected. Fixed in `integration/contract.py` (`_fresh`: a deterministic uuid),
`plugins/relations.py`, `plugins/concurrency.py` and `plugins/rules.py` (scenarios that need an open record are
dropped when none is). On the failing app's own mocks: 5 failed before, 84 of 84 pass after. Test:
`tests/test_contract_scenarios.py` (the draft kept as `fixtures/scenario-specs/volunteer-shifts.json`).
