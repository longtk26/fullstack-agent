# Story 18.11 — Lean backend validation: no test-writing step; the app starts and its API answers

**Epic:** [18 — Generation speed](epic18_generation_speed.md) · **Requirements:** FR-09, FR-11, FR-30 · **Depends on:**
6.x, 17.5, 17.6, 19.5

## User story

As a user, I want the backend lane to finish once the app starts and its API answers as planned, without an engine
step that writes tests and without repair rounds over style findings, so that a backend with a custom operation takes
minutes rather than twenty or more and fails only when the app is really broken.

## Evidence

- **2026-11-04, `gen_01M6J88EY82D746ZG01MB7WE77` (Antigravity, dynamic):** `generate_backend` 883 s,
  **`generate_tests` 405 s**, `run_validation` 15 s for all eight checks. A third of the backend lane went into
  engine-written tests; the checks themselves take seconds.
- **2026-11-03, gym and money-tracker drafts:** `generate_tests` made one engine call per module with a custom
  operation (gym: 274 s + 209 s). `complete_backend@v2` already asks for "comprehensive API tests", so tests are
  asked for twice. CRUD tests come from the templates (17.6) in under a second and are always right.
- **Repairs on what the app does not need:** index-name and constraint details of the migration check started repair
  rounds although the app ran.
- **Repairs on generator-owned files:** 30 minutes of `repair_frontend` on a generated `tests/unit/api.test.ts` (a
  generator bug the engine may not edit); the engine then broke a convention working around it. The backend has the
  same exposure for its template tests.

## Steps

1. **Remove the `generate_tests` node.** The backend lane becomes `plan_architecture → generate_database →
   generate_backend → run_validation ⇄ repair_code` in backend and dynamic mode (`graph.py`: both graphs,
   `_display_graph`, `BACKEND_LANE_NODES`; `state.py` node lists; `runner.py`; the fake engine's purposes; the UI's
   step labels and lane progress). `generate_backend` writes the template tests (`module_tests`, recorded as owned)
   together with the CRUD code. No engine call writes tests: `PROMPT_VERSIONS` drops `generate_tests` (the prompt
   files stay as history), and `complete_backend@v3` no longer asks for tests. `runTests=false` still skips running
   the template tests. A job checkpointed on the old graph restarts from the beginning when resumed (as
   `SPEC_INVALID` continues do).
2. **Blocking checks prove the app starts and the API works; the rest are warnings.** Each check result gets
   `blocking: true | false`; only blocking failures start `repair_code` or fail the lane:

   | | Checks |
   |---|---|
   | **Starts** (blocking) | `deps` (install), `syntax`, `migration` **upgrade to head** on an empty database, `startup` (app boots, `GET /health` → 200) |
   | **API works** (blocking) | `openapi` (the started app's OpenAPI against the contract / plan), `tests` (template CRUD tests), `smoke` (step 3) |
   | Warning (recorded, never repaired) | `lint`, `conventions`, migration downgrade / re-upgrade and schema details (planned index and constraint names, extra indexes) |

   Warnings run only after the blocking checks pass. A lane with warnings ends `COMPLETED_WITH_WARNINGS`; the digest
   for a repair round lists only blocking failures, and the UI lists warnings apart ("Completed with 2 warnings:
   lint, conventions").
3. **Smoke step for custom operations** (in the `tests` check, no engine): after startup, call each custom operation
   once against the seeded database (path parameters from the seed, query parameters left out, a request body built
   from the contract's request schema and the seed) and require the operation's planned status (else 2xx) and a body
   that matches the contract's response schema. Failures name the operation, the request and the response, so a
   repair round has what it needs.
4. **Stop on generator-owned failures.** Before `repair_code`, if every blocking failure is in a file the generator
   owns (`owned.json`), do not call the engine: end the lane with a clear "generator bug" error naming the files and
   checks, in seconds. Mixed failures repair only the non-owned ones and say so in the prompt. (Same rule as 18.10
   step 4 for drafts.)
5. **Docs.** FR-09's node list and FR-11 (validation) in `requirements.md`, `docs/business-workflow.md`,
   `docs/technical-architecture.md`, the LangGraph diagram (`docs/diagrams/langgraph-workflow.drawio`),
   `docs/engines/antigravity.md`.
6. **Tests.** The graphs without `generate_tests` (and `describe_graph` snapshots); check classification and the
   warning outcome; `repair_code` sees only blocking failures; the smoke step on the golden two-entity project with a
   custom operation (pass, wrong status, schema mismatch); a failure only in a template test stops without an engine
   call; prompt snapshot of `complete_backend@v3`.

## Acceptance criteria

- [x] The backend lane has no `generate_tests` step, and no engine call writes tests; the template tests are written
      with the backend code.
- [x] Only the "starts" and "API works" checks start repairs or fail the lane; lint, conventions and migration
      details are warnings, ending the lane `COMPLETED_WITH_WARNINGS`, listed in the UI.
- [x] Every custom operation is called once after startup and must answer as the contract says.
- [x] A failure only in generator-owned files ends the lane at once as a generator bug, with no engine call.
- [ ] Measured with the fake engine: backend lane time without `generate_tests`; then, with the user's yes (paid
      engine), on the gym and money-tracker drafts: lane time, engine calls and outcomes recorded in the Status.

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test` (sandbox checks), `cd agent-ui && pnpm exec tsc --noEmit`.
With the fake engine: a CRUD project and the golden project with a custom operation complete; a planted lint finding
gives `COMPLETED_WITH_WARNINGS` with no repair; a planted bug in a template test stops at once; a custom operation
that returns the wrong shape starts one repair round naming it.

## Status

**Planned (2026-11-03)**, at the user's request, after the gym and money-tracker runs.
**Re-scoped (2026-11-04)**, at the user's request: the `generate_tests` node is removed (not just made optional, so no
`thoroughTests` option), validation only proves the app starts and its API works, and the story covers the backend
lane only. Moved out: the frontend lane's blocking / warning split and the `complete_backend` context pack with
parallel modules, now [18.13](story18.13_backend_context_pack.md).

**Implemented (2026-11-04)**, on `feat/story18.12-lane-previews` (after 18.12):
- The `generate_tests` node is gone from both graphs, the display graph, `state.py`, the runner's prompt list, the
  engine purposes and the fake scenarios; `generate_backend` writes `module_tests` with the CRUD code (owned when
  the module has no gaps; skipped with `runTests=false`). `complete_backend@v4` no longer asks for tests (v3 stays).
  The planner still lists a "happy path" test per custom operation (plan snapshots unchanged); the `tests` check now
  requires only the CRUD ones (`ValidationRequest.required_tests`), none on the engine path.
- Warnings are a check status, `warning` (failed, not blocking), instead of a `blocking` flag: `failed_checks`, the
  digest and the repair loops already look at `failed` only, and later checks treat `warning` as passed. `lint` and
  `conventions` report `warning`; `migration` blocks only on autogenerate + `alembic upgrade head`
  (`upgrade_migration`), while check / downgrade / upgrade (`roundtrip_migration`) and the schema-vs-plan details
  are a warning. The runner ends a job whose last run has warnings `COMPLETED_WITH_WARNINGS` (`CHECK_WARNINGS`,
  "Completed with N warning(s): …"); the UI badges `warning`.
- Smoke step (`checks/smoke.py`): one call per non-CRUD operation (aggregates included), path parameters from the
  contract fixtures, request bodies from the request schema and the fixture; the sandbox seeds the migrated database
  through the overlay's `scripts/seed.py`, serves the app and makes the calls (`.bga/smoke.py`); the worker judges
  status and response schema (reusing the live checks' `validate_value_against_schema`). Backend mode builds the
  contract from the spec. Operations behind auth or without fixtures for their path are skipped and named.
- Generator bug: when every blocking failure names only owned files, the lane stops at once (`GENERATOR_BUG`, no
  engine call). Deviation: a failing `tests` check never counts (a failing test names its test file whatever broke),
  nor does a failure without a file (a startup crash). Mixed failures add a line to the digest naming the owned files.
- First real catch: the golden flashcards completion (fake engine) was stale against the templates — a wrong DTO
  import, `CardRepository.list()` called without `q` (500 on `card.listDue` and `deck.stats`) and snake_case
  `due_today` where the contract says `dueToday`. Its engine-written tests never ran (async without a plugin).
  Fixed the golden; removed its tests (the engine writes none now).
- Tests: `test_lean_validation.py` (smoke calls, judging, sample bodies, warnings, generator bug), the sandbox
  pipeline tests on the new statuses, and `test_custom_operations_answer_the_smoke_calls` (flashcards in the Docker
  sandbox: three custom operations answer as the contract says).
- Still open: the paid gym / money-tracker measurement (needs the user's yes).

**Found (2026-11-04), `gen_01M6JMBCKWQ8TZ4TMW2FJ6TWJ6`** (Antigravity, soccer-field draft; cancelled): `frontend:typecheck`
failed three rounds on the same 10 errors in the generated `src/lib/api/types.ts` (`Duplicate identifier 'fieldId'`),
which the engine may not edit. The drafted spec had `GET /fields/{fieldId}/reviews` with `filters: ["fieldId"]`; the
contract added the filter as a query parameter next to the path parameter of the same name. The backend templates
had the same gap: a nested list ignored its path (the router dropped the path parameter from the use-case call) and
its template tests called `"/fields/{fieldId}/time-slots"` with the braces in it. No example spec had a nested list.
Fixed:
- `planner.py`: a list's path parameter that names a column is a filter with `"in": "path"` (whether or not the
  spec lists it), never a second query filter; `contract.py` adds no query parameter for it; the router passes the
  path value (typed by the column) to the use case; the template tests seed every record under one parent and call
  the real URL (`_list_scope`), and `filter_<param>` checks that a record under another parent stays out. The
  frontend mock filters a list by its path parameters.
- Found by the new sandbox test: a module with two lists (`GET /tasks` and `GET /projects/{projectId}/tasks`) wrote
  the DTO and use case of only one (the module's CRUD operations were keyed by action), so the app failed to start.
  `_Module.lists` now writes every list; search is per list (the repository searches the fields of all of them).
- The generator-bug stop now covers the frontend lane too (`generator_bug_files`, moved to `validation.py`): a
  frontend failure only in owned files ends the lane at once (dynamic: `frontend_error`; static: `GENERATOR_BUG`).
  A failing `conventions` check never counts, since it names the owned file the engine changed.
- Tests: `test_scoped_lists.py`; sandbox `test_a_list_scoped_by_its_path_passes_its_template_tests`.

**Found (2026-11-04), `gen_01M6JQ7F280RY8FJY21JJZDDDS`** (Antigravity, the same draft after the fix above; cancelled
in `repair_code`): every check passed (40 template tests included) except the smoke step, whose two "failures" were
right answers to bad guesses: `booking.create` sent the seeded booking's own slot and got 409 (slot taken), and
`booking.cancel` sent `"bookingId": "Sample"` and got 404. A repair round on correct code followed. Fixed in
`checks/smoke.py`: a 400 / 404 / 409 with the error envelope counts as a business rule answering (named in the
summary, never a failure; 5xx, 422, no envelope or a wrong shape still fail); `<entity>Id` body fields take a
seeded record's id, and a create (`POST` without path parameters) takes the first seeded references instead of its
own seeded record's. Tests in `test_lean_validation.py`.

**Status (2026-11-06): one call per endpoint, no 5xx.** The `tests` check (`BACKEND_TESTS=false`: the smoke calls only)
calls each endpoint once: its first success scenario from the contract (real ids, a body, the demo user it runs as),
else a call built from the fixtures (custom operations), then runs the job worker once. It fails only on a 5xx, no
answer or a crashing worker; any 2xx / 4xx passes, and statuses, error codes and response shapes are no longer
compared with the contract (exact checks made correct apps fail: `gen_01M6RMDDVK0XNDP1TKR25Z45AQ` was refused for a
moderator-only 403 and role-guarded 401s). `RULE_ANSWERS` / `rule_answer` and the delivered-webhook, settled-payment
and inbox checks were removed. The seed stays strict: it is our data, so a seed that cannot be inserted fails the
check (summary names the error, e.g. the `IntegrityError`); `build_fixtures` maps a seeded foreign key no parent
record has onto one (`gen_01M6RJ17148HNE5MWEK0QKDZKA`: drafted recipe owners vs. the auth plugin's demo users).
Verified: `gen_01M6RNS949KSV5QKARTS1ENA46` (Antigravity) passed run_validation on attempt 1.
