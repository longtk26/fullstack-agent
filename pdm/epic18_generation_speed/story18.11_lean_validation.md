# Story 18.11 — Lean validation: the app starts and every API answers

**Epic:** [18 — Generation speed](epic18_generation_speed.md) · **Requirements:** FR-30 · **Depends on:** 6.x, 17.5,
17.6, 19.5

## User story

As a user, I want a generation to finish once the app starts and every API answers as the contract says, without
waiting for engine-written tests or repair rounds over style findings, so that a backend with a custom operation
takes minutes rather than twenty or more and fails only when the app is really broken.

## Evidence (2026-11-03, Antigravity, gym and money-tracker drafts)

- **Engine-written tests.** `generate_tests` makes one engine call per module with a custom operation (gym: 274 s +
  209 s). `complete_backend@v2` already asks for "comprehensive API tests", so tests are asked for twice. CRUD tests
  come from the templates (17.6) in under a second and are always right.
- **Repairs on what the app does not need.** Frontend: a `conventions` finding (`interface` instead of `type`) failed
  the lane after three repairs. Backend: index-name and constraint details of the migration check started repair
  rounds although the app ran.
- **Repairs on generator-owned files.** 30 minutes of `repair_frontend` on a generated `tests/unit/api.test.ts` (a
  generator bug the engine may not edit); the engine then broke a convention working around it.
- **`complete_backend` re-reads everything.** The prompt names `spec.json` (19 KB), `plan.json` (56 KB) and
  `contract.json` (49 KB) by path and asks to read the module's files first: 45 reads and 53 turns (~8 min) before
  the first write, per module, modules one after the other (gym: 508 s + 394 s).

## Steps

1. **Blocking and warning checks.** Only what proves the app works blocks; the rest is recorded and shown, and the
   job ends `COMPLETED_WITH_WARNINGS` instead of repairing:

   | Lane | Blocking | Warning |
   |---|---|---|
   | Backend | `syntax`, `deps`, `startup`, `migration` (upgrade / downgrade / upgrade; planned tables, columns, foreign keys, enums), `openapi` (contract conformance), `tests` (template CRUD tests + the smoke step below) | `lint`, `conventions`, `migration` details (index and constraint names, extra indexes) |
   | Frontend | `install`, `typecheck` (app code), `build`, `routes`, `tests` (generated API and form tests) | `lint`, `conventions`, `assets` (as today), `journeys`, type errors only in test files |

   Each check result gets `blocking: true | false`; the repair loops (`repair_code`, `repair_frontend`) see only the
   blocking failures; the digest and the UI list warnings separately ("Completed with 3 warnings: lint, …").
2. **Smoke step for custom operations** (backend `tests` check, no engine): after startup, call each custom
   operation once against the seeded database (path parameters from the seed, query parameters left out, a request
   body built from the contract's request schema and the seed), and require a 2xx (or the operation's planned
   status) and a body that matches the contract's response schema. Failures name the operation, the request and the
   response, so a repair round has what it needs.
3. **No engine-written tests by default.** `generate_tests` writes only the template tests and makes no engine call;
   `complete_backend` (next version) no longer asks for tests. An option `thoroughTests` (default off) restores the
   engine-written tests for a generation that wants them.
4. **Stop on generator-owned failures.** Before a repair round, if every blocking failure is in a file the generator
   owns (`owned.json`, both lanes), do not call the engine: end the lane with a clear "generator bug" error naming the
   files and checks, in seconds. Mixed failures repair only the non-owned ones and say so in the prompt. (Same rule
   as 18.10 step 4 for drafts.)
5. **`complete_backend` context pack.** The next prompt version inlines what a module needs: each custom operation's
   spec entry and contract operation (schemas resolved), the fields of the models it touches, the module's plan entry
   (as today), and one example of each generated file kind (port, repository, use case, router, DTO); it says that
   everything needed is in the prompt and not to read other files. Modules with custom operations run in parallel,
   each in its own scratch copy (as custom components do, 17.3), and their changes are merged back; a conflict falls
   back to running them one after the other.
6. **Tests.** Check classification and the warning outcome; repair loops skip warnings; the smoke step on the golden
   two-entity project with a custom operation (pass, wrong status, schema mismatch); generator-owned failures stop
   without an engine call; prompt snapshot of the new `complete_backend` version; parallel modules merge.

## Acceptance criteria

- [ ] Only the blocking checks above start repairs or fail a generation; warnings end it as
      `COMPLETED_WITH_WARNINGS` and are listed in the UI.
- [ ] Every custom operation is called once after startup and must answer as the contract says.
- [ ] No engine-written tests unless `thoroughTests` is set.
- [ ] A failure only in generator-owned files ends the lane at once as a generator bug, with no engine call.
- [ ] `complete_backend` reads no project files beyond what its prompt carries in the usual case (≤ 15 turns), and
      modules run in parallel.
- [ ] Measured on the gym and money-tracker drafts: backend lane ≤ 6 min (from ~20–40 min), frontend lane unchanged
      or faster.

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test` (sandbox checks). With the fake engine: a CRUD project and
the golden project with a custom operation complete; a planted lint finding gives `COMPLETED_WITH_WARNINGS`; a
planted bug in a generated test stops at once. Then, **with the user's yes** (paid engine), regenerate the gym and
money-tracker drafts and record the lane times, engine calls and outcomes in this story's Status.

## Status

**Planned (2026-11-03)**, at the user's request, after the gym and money-tracker runs.
