# Story 23.11 — Engine-written view slots (opt-in experiment)

**Epic:** [23 — App design](epic23_app_design.md) · **Requirements:** FR-37, FR-30 · **Depends on:** 23.10

An experiment behind a flag, run only when the user asks after Checkpoint D. Epic 22's D5 (no engine call in the
frontend lane) stays the default.

## User story

As a user who wants a look the kit doesn't have, I want the code engine to write the app's shell, cards, list views
and home for my product, while the data, the forms and the API calls stay the tested kit's, so that the app looks
custom and still works with its backend.

## Context

- Story 17.3 has the machinery: custom components written in parallel, validated, and cached by content
  (`frontend/custom_components.py`, `component_cache.py`), with a kit fallback.
- What breaks integration is code that calls the API or writes forms. The slots never do: they get data and actions
  as props.

## Steps

1. **Flag.** `APP_VIEW_SLOTS=off` (default) or `engine`; per generation in the options. Listed in
   `docs/development/test-doubles.md` only if a test switch is added.
2. **Slots and their props.** Four slots: `Shell` (nav items, user, area switcher, children), `RecordCard` per entity
   (record, field roles, actions from `allowedActions`, `onAction`), `ListView` per entity (records, paging, filters
   state, `renderCard`), `HomeView` (the home's sections, already bound). Codegen writes `src/components/app/slots.d.ts`
   with exact types from the contract. Data hooks, forms, auth, mocks and `lib/api` stay owned files
   (`.bga/owned.json`); a slot importing from `lib/api` or calling `fetch` fails the `conventions` check.
3. **Generation.** With the flag on, after the planner: phase 1, one engine call for shared primitives (the recipe's
   surfaces as components); phase 2, the slots in parallel, each with a context pack (the brief, the recipe tokens,
   the entity's fields and roles, the props type, two kit examples). Each slot is validated alone (typecheck, lint, a
   render test on fixture records, the design check at 375 / 1440 px); a failing slot gets one repair, then the kit's
   view is used and noted. Validated slots are cached by content key.
4. **Integration unchanged.** Scenarios, the pair check and the live switch run as without slots; the app walk
   must pass with slots on.
5. **Measure** (fake engine first, then one paid run only with the user's yes): engine calls, time added to the
   frontend lane, slots that fell back, the report's similarity with and without slots, cache hits on a second run.
6. Tests: the props types per entity, the conventions rule, fallback on a failing slot (fake engine), the cache key.

## Acceptance criteria

- [x] With the flag off, nothing changes (0 engine calls in the frontend lane).
- [ ] With the flag on, slots render the golden apps; a slot that fails twice falls back to the kit with a note, and
      the app still builds and passes the app walk.
- [x] No slot can call the API or render a form (the conventions check refuses it).
- [ ] The measurement is in the Status, and the user decides whether slots stay, become default for some archetypes,
      or are dropped.
- [x] Static golden passes.

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test`, `make up` with `APP_VIEW_SLOTS=engine` on the fake engine.
Paid engine only with the user's yes.

## Status

**Implemented as an opt-in experiment (2026-11-06), off by default; measured on the fake engine only.**
- `APP_VIEW_SLOTS=off|engine` (and `options.viewSlots`); with it on, `generate_frontend` makes one engine call per slot
  (the shell, up to three record cards) with `generate_view_slot@v1`, against fixed props (`slot-types.ts`); code
  refuses a slot that calls fetch, imports `@/lib/api`, loads data, renders a form or reads storage, or has no default
  export (`slots.refusal`), and the kit's view is used. The registry `slots.ts` (generator-owned, updated in
  `.bga/owned.json`) names the accepted ones; the kit uses a slot only when registered.
- Fake engine: `write_view_slot` (and a planted `fetch`); `make app-design-report ARGS="--slots"` builds apps with the
  fake slots (video library, event tickets: 0 failures).

Deviations: one attempt per slot, no repair round (a refused slot falls back at once); no cache yet; the measurement
with a real engine, and the decision to keep slots, are the user's.
