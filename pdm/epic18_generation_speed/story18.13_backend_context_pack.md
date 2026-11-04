# Story 18.13 — `complete_backend` context pack, modules in parallel; frontend warnings

**Epic:** [18 — Generation speed](epic18_generation_speed.md) · **Requirements:** FR-30 · **Depends on:** 18.11, 17.3

Split out of 18.11 on 2026-11-04, so that 18.11 stays the backend validation change the user asked for first.

## User story

As a user, I want the engine to write a backend module's custom operations from what its prompt carries, all modules
at once, and the frontend lane not to repair style findings, so that `generate_backend` takes a few minutes and the
frontend lane fails only on real faults.

## Evidence

- **`complete_backend` re-reads everything.** The prompt names `spec.json` (19 KB), `plan.json` (56 KB) and
  `contract.json` (49 KB) by path and asks to read the module's files first: 45 reads and 53 turns (~8 min) before
  the first write, per module, modules one after the other (gym 2026-11-03: 508 s + 394 s; 2026-11-04 run:
  `generate_backend` 883 s).
- **Frontend repairs on style.** A `conventions` finding (`interface` instead of `type`) failed the frontend lane
  after three repairs.

## Steps

1. **Context pack.** The next `complete_backend` version inlines what a module needs: each custom operation's spec
   entry and contract operation (schemas resolved), the fields of the models it touches, the module's plan entry (as
   today), and one example of each generated file kind (port, repository, use case, router, DTO). It says that
   everything needed is in the prompt and not to read other files.
2. **Modules in parallel.** Modules with custom operations run in parallel, each in its own scratch copy (as custom
   components do, 17.3), and their changes are merged back; a conflict falls back to running them one after the
   other.
3. **Frontend blocking and warning checks** (the 18.11 mechanism on the frontend lane): blocking `install`,
   `typecheck` (app code), `build`, `routes`, `tests` (generated API and form tests); warning `lint`, `conventions`,
   `assets` (as today), `journeys`, type errors only in test files. Generator-owned failures stop at once (18.11
   step 4) for `repair_frontend` too.
4. **Tests.** Prompt snapshot of the new version; parallel modules merge, and a conflict runs them in sequence;
   frontend classification and the warning outcome.

## Acceptance criteria

- [x] `complete_backend` reads no project files beyond what its prompt carries in the usual case (≤ 15 turns), and
      modules run in parallel. *(Prompt side done and tested; the turn count needs the paid measurement below.)*
- [x] Frontend style findings are warnings; only the blocking frontend checks start repairs.
- [ ] Measured with the user's yes (paid engine) on the gym and money-tracker drafts: backend lane ≤ 6 min (from
      ~20–40 min), frontend lane unchanged or faster.

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test`. With the fake engine: two modules with custom operations
complete in parallel; a planted frontend `conventions` finding gives `COMPLETED_WITH_WARNINGS`.

## Status

**Done (2026-11-04)**, except the paid measurement (open, only with the user's yes).

- **Context pack** (`orchestrator/backend_completion.py`, `module_context`): the new `complete_backend@v5` inlines,
  per module, each custom operation's plan entry, spec entry, named rules and contract operation (local `$ref`s
  resolved, mock plans and samples left out); the module's generated source files whole (up to 48 KB, else the files
  the engine edits plus one example of each kind; empty packages skipped); its entity and model; the entities and
  repository ports of related modules (foreign keys both ways plus entities the operations name, with the `Dep`
  import line); and the exception helpers. The prompt says everything is there and not to read other files; spec,
  plan and contract paths stay as a fallback. The file tree is gone. Flashcards: `decks` 26 KB, `cards` 37 KB
  (before: 124 KB of JSON named by path, plus the reads: 45 reads and 53 turns, ~8 min, before the first write, per module on the gym run).
- **Modules in parallel** (`complete_modules`): one scratch copy per module (`<workspace>/scratch/module-<name>`,
  without `.git`, `.venv`, caches, `.claude`, `.agents`), at most `ENGINE_CONCURRENCY` engine calls; changes are
  compared by content and merged in plan order; adapter files (dot folders, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`)
  are never merged. A module that changed a file an earlier module changed differently runs again in the project on
  the merged code; the same change from two modules is not a conflict. One module, or `ENGINE_CONCURRENCY=1`, runs in
  the project directly. The step summary adds `parallel` and `conflicts`.
- **Frontend warnings** (`frontend_validation.py`): `conventions` findings are `warning`s, and so are type errors
  only in test files (`tests/`, `*.test.ts(x)`, `*.spec.ts`, and only when every error line was parsed; the parser
  now reads `tests/` paths too). The generator-owned stop already applied to `repair_frontend` (18.11).
- **Deviation:** frontend unit tests, Playwright smoke, journeys and ESLint have been skipped in validation since
  2026-11-01 (`95b547b`), so step 3's blocking list is `install`, `typecheck`, `build`, `routes` (plus `assets` as
  before); `tests` and `journeys` stay skipped until someone turns them back on.
- **Tests:** `tests/test_backend_completion.py` (related entities, pack contents, v5 prompt, parallel merge,
  conflict rerun, same change, one module, the flashcards run with both engine calls overlapping, frontend
  warnings). The two lane-failure tests in `test_parallel_generation.py` used the planted conventions finding to fail
  the frontend; they now use `FailingFrontendValidator`. `test_component_cache.py`'s usage assertion now counts only
  its own cache hits (the session-wide test database also holds the sandbox tests' runs, so it failed with
  `BGA_SANDBOX_TESTS=1`).
- **Verified:** `make lint`; `make test` and `BGA_SANDBOX_TESTS=1 make test` (889 passed; the one failure was the
  order-dependent cache test above, fixed and re-run). `make up`, then a dynamic flashcards generation on the fake
  engine (`gen_01M6K0300WW56MHRSGWAHD72JM`): COMPLETED in 2 min 49 s, all three lanes completed, `generate_backend`
  `{"parallel": true, "conflicts": [], "engineCalls": 2, "completedByEngine": ["decks", "cards"]}`, backend
  validation passed with the merged code. The conventions warning is covered by tests; the flashcards site is
  rendered, so it has no planted finding.
