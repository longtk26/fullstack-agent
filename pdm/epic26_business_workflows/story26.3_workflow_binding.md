# Story 26.3 — Workflow binding at draft time

**Epic:** [26 — Main business workflows](epic26_business_workflows.md) · **Requirements:** FR-40 · **Depends on:** 26.2

## User story

As the agent, I want each workflow step tied to the operation, page and action that perform it in this app, checked
against the contract, so the guided tour and the evaluation point at the same real controls.

## Context

The lab's `bind` stage (`bind_prompt`, `BIND_SCHEMA`, validation in `stage_bind`): actors → roles; records → entity,
get and list operations, status field and values; setup (existing records a path needs); per step the operation, path
params, query, body with `{{record}}` / `{{user.<role>.id|email}}` / `{{run}}` variables, `creates`, `automatic` (the
app does it inside the previous step), the page and its params; effects (what to read before and after); outcomes
(page per actor). Lessons: give the binding each path's rules (thresholds); validate every name against the contract;
list unbound items as findings.

## Steps

1. **Binding call** (prompt `bind_workflows@v1`) in `draft_app` after the contract is built, through the provider.
2. **Code validation:** operations, pages, roles, entities, status values (enum), fields; what does not match is a
   binding problem with its reason, never silently dropped.
3. **The action target.** For each step, the kit's section and action that perform it in the UI (`app.json`: page →
   section → action id, from the operation), so the tour can point at it.
4. **Stored**: `app.json` gains `workflows` (per role: the core workflow paths, their steps with page, action target,
   text) for the tour; the full binding is packaged as `binding.json` for the evaluation.
5. Tests: validation of each kind of name, the action target found for custom operations, transitions and create
   forms, snapshots for the three lab drafts.

## Acceptance criteria

- [ ] Every core step has an operation and a page, an `automatic` mark, or a binding problem that says why not.
- [ ] Every action target in `app.json` `workflows` exists in the generated screens (checked by a test on the kit's
      planned sections).

## Verify

`make lint`, `make test`, a lab draft on the fake provider.

## Status

Open (2026-11-07): the action targets were checked by a unit test only, not on generated screens (the kit hides actions by role and `allowedActions`); 26.7.

2026-11-07: `check_binding(..., business)` now reports every core step (main path and branches) the binding left out or bound without a page, unless the model already listed it in `unbound` (test `test_every_core_step_is_bound_or_has_a_problem`).

**Done 2026-11-07.** `BusinessFlow.bind` (prompt `bind_workflows@v1`) after `draft_app`, against the drafted contract and
planned screens (`compact_operations`, `compact_pages`, the demo users per role from the extended spec);
`check_binding` checks operations, pages, roles, status values and the JSON of every call; problems are kept with
their reasons. `action_targets` finds the action, form submit or data section that performs each step;
`tour_workflows` writes `app.workflows` (per core workflow: steps with role, page, route and target).

Real run (HomeFix): 14 steps bound, one problem the app really has (no maintenance report record, only dashboard
figures). Steps that only look at something first had no target; they now point at the section that shows the data
(test added). Deviation: no snapshots of the three lab drafts' bindings (each binding is a model answer; the code
check is tested on its own).
