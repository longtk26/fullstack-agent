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

- [ ] `complete_backend` reads no project files beyond what its prompt carries in the usual case (≤ 15 turns), and
      modules run in parallel.
- [ ] Frontend style findings are warnings; only the blocking frontend checks start repairs.
- [ ] Measured with the user's yes (paid engine) on the gym and money-tracker drafts: backend lane ≤ 6 min (from
      ~20–40 min), frontend lane unchanged or faster.

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test`. With the fake engine: two modules with custom operations
complete in parallel; a planted frontend `conventions` finding gives `COMPLETED_WITH_WARNINGS`.

## Status

**Planned (2026-11-04).**
