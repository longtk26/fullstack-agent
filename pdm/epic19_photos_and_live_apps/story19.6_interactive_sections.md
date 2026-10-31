# Story 19.6 — Interactive sections

**Epic:** [19 — Real photos and API-driven dynamic apps](epic19_photos_and_live_apps.md) · **Requirements:** FR-32 · **Depends on:** 19.5, 17.4

## User story

As a user of a dynamic app, I want to edit, delete, filter, search, sort, page through and act on my records from
the generated screens, so that the app does what its API can do.

## Context

- Typed section content: `modules/shared/domain/frontend_spec/section_props.py` (`DataSectionProps`,
  `CardGridProps`, `FormProps`, `StatsProps`, `SECTION_PROPS`); catalogue descriptions:
  `frontend_spec/catalogue.py` (`BUILTIN_SECTIONS`); the drafter's list: `drafting.section_catalogue()`.
- Data binding and forms: `frontend_spec/schema_v1.py` (`DataBinding`, `Form`, `OnSuccess`). A `Form` has
  `operationId` and `params` but no way to load the current record.
- Rendering: overlay `templates/nextjs_overlay/files/renderer/src/components/sections/*.tsx`,
  `renderer/use-section-records.ts`; generated per site by `orchestrator/frontend_renderer.py` (site.json, registry,
  props types) and `orchestrator/frontend_codegen.py` (`bindings_ts`, `queries_ts`, `query_keys_ts`, `forms_ts`).
- The backend already supports list `filters`, `sort` and `search` (BackendSpec `Operation`, `planner.py`); the
  contract exposes them as query parameters, and the mocks honour them.
- Pair check: `orchestrator/checks/consistency.py` (`bindings`, `forms`, `parameters`).

## Steps

1. **Actions on data sections.** `DataTable`, `CardGrid`, `List` and `DetailView` content gets
   `actions: [{id, label, kind: "link" | "mutation", page?, params?, operationId?, body?, confirm?, variant?,
   onSuccess?: {toast?, navigate?}}]`:
   - `link`: to a page (record params from the row, e.g. `{"id": "$record.id"}`);
   - `mutation`: calls an operation (CRUD `update` / `delete` or any custom operation); `body` values may be fixed
     or `$record.<field>`; `confirm` shows a dialog (required for DELETE);
   - rendered as row buttons (DataTable), a card footer (CardGrid, List) or a button bar (DetailView); each button
     has `data-bga-action="<id>"`.
2. **Standalone `ActionBar` section** for operations not tied to a listed record: buttons, each a `mutation` with
   `params` (e.g. `$route.id`) and `body` (e.g. `{"rating": "good"}`); used for the "Again / Hard / Good / Easy"
   style choices. It may sit inside a layout node next to a `DetailView`.
3. **Edit forms.** `Form` gets `load: {operationId, params}`: a GET returning the form's record; the form shows a
   loading state, then pre-fills its fields; submit sends the update (PATCH: only changed fields; PUT: all). Pair
   check: `load` is a GET whose response has the form's fields.
4. **List controls.** Data sections bound to a list operation get
   `controls: {search?: bool, filters?: [field], sort?: [field], pageSize?: int}`; only what the operation declares
   (contract query parameters) is allowed (pair check `CONTRACT_PARAM_MISMATCH` otherwise). State lives in the URL
   query (`useSearchParams` + `router.replace`), so a filtered view can be shared; pagination uses `limit` /
   `offset` and the list response's total when there is one.
5. **Stats from data.** `Stats` items may take `data: {operationId, value: "count" | "<field>"}`: `count` = the list
   total (or length); a field = that field of a GET response (e.g. a custom `deck.stats`).
6. **Fresh data after changes.** Every mutation (forms and actions) invalidates the list and detail queries of its
   entity (`query_keys_ts`), so lists, details and stats update without a reload. Check what `useOperationMutation`
   does today and extend it there, once.
7. **Hooks for tests.** Sections carry `data-bga-section="<section id>"`; record rows / cards carry
   `data-bga-record="<primary key>"`; actions carry `data-bga-action` (step 1). 19.9 relies on them.
8. **Library plumbing.** Typed props (section_props.py), catalogue descriptions, `section_catalogue()`, the
   renderer's per-site selection (only sections a site uses are copied), props types, pair checks for every new
   binding, the smoke test's expected text (`frontend_codegen.smoke_spec`), `DESIGN_CHECKLIST.md` (buttons,
   dialogs, focus, empty and loading states use theme tokens), and conventions.
9. **Examples.** Update `examples/frontend-specs/project-tracker-dynamic.json` (or `shop-dynamic.json`) to use row
   actions, an edit form with `load`, and list controls, so the golden fake runs cover them.
10. Tests: Python (props validation, pair checks for actions / load / controls / stats, site.json snapshot);
    sandbox (vitest for each new section on the mock API: delete with confirm removes the row, edit pre-fills and
    saves, search narrows the list, an action updates a stat); design check.

## Acceptance criteria

- [x] Data sections support link and mutation actions (with confirmation for deletes), and `ActionBar` exists.
- [x] Forms can load a record and save it as an update.
- [x] Lists offer the search, filters, sort and paging their operation declares, kept in the URL.
- [x] Stats can show counts and fields from the API.
- [x] Mutations refresh the affected lists, details and stats.
- [x] Pair checks reject actions, loads and controls that do not match the contract.
- [x] `DESIGN_CHECKLIST.md` holds; sandbox and snapshot tests pass.

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test`, `node scripts/design-check.mjs` (as the checklist
describes), `make up` with the fake engine: the updated dynamic example COMPLETED, and in the preview (mock API)
edit, delete, search and an action work.
