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
