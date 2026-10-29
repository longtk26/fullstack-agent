# Story 17.4 — Data sections for dynamic apps

**Epic:** [17 — Fast generation](epic17_fast_generation.md) · **Requirements:** FR-30, FR-25 · **Depends on:** 17.2, 13.2

## User story

As a user generating a dynamic web app, I want the frontend lane to finish in minutes, so that the total time is
set by the backend and not by page writing.

## Acceptance criteria

- [x] Codegen emits an `operationId → hook` map next to the generated `queries.ts`; the library's data sections
      (`CardGrid`, `DataTable`, `DetailView`, `List`, `Form`) take a `DataBinding` and use that map, so one
      component serves every resource (fields, params, route parameters, pagination, sorting).
- [x] Loading, empty and error states come from `sections[].states`; forms use the generated Zod schemas
      (`src/lib/forms.ts`) and the operation's mutation hook, and `onSuccess` navigates or refreshes as the spec
      says.
- [x] `project-tracker-dynamic` generates with no engine call on the frontend lane; the mock layer, the
      `MOCK_TEST_API` switch and the live smoke tests (Epic 14) pass unchanged.
- [x] Status note records the frontend-lane time and which lane now sets the total.

**Status (2026-10-29):** done. Done before 17.3: every custom component in the examples is a dynamic data component.

- Generated per site: `src/components/renderer/bindings.ts` (`frontend_codegen.bindings_ts`): every operation's
  fetcher and the same query keys as `queries.ts`, behind two generic hooks, `useOperationQuery(operationId,
  params)` and `useOperationMutation(operationId)` (mutations refresh the resource's lists). **Deviation:** two
  generic hooks over maps instead of a map of the per-operation hooks, so no component picks a hook at runtime.
  `src/components/renderer/form-schemas.ts` maps form ids to the generated Zod schemas and defaults. `site.json`
  carries each binding (operation, params, columns with labels and formats from the contract — dates, enums as
  badges — and a link to the record's own page when one exists) and the form definitions.
- Library: `CardGrid`, `List`, `DataTable` (client components; a content collection or a list operation),
  `DetailView` (a get operation), `Form` + `use-section-form.ts` (RHF + the generated Zod schema, hidden
  `$route.*` fields, the operation's mutation, toast / navigate / reset), `QueryState` (states from the spec),
  `use-section-records.ts` (`$route.*` params from the URL). The **sidebar shell** joined the library
  (`SiteShell.sidebar.tsx`, copied as `SiteShell.tsx` when the spec asks for it): the tracker uses it.
- The planner installs exactly the shadcn primitives the copied library files import (`library_primitives`).
  `rendererGaps` for dynamic specs: custom components (17.3), content sections bound to an operation, forms with
  unsupported field types; static forms (no operation) stay an engine case.
- Fake engine: `project-tracker-dynamic` needs no frontend engine, so its golden frontend is removed; tests of the
  frontend lane's engine path (concurrency, cancel, resume, a failing frontend lane) use the shop pair.
- **Timings** (`make up`, fake engine for the backend lane):

  | `project-tracker-dynamic` + `two-entity` | 17.5 run | now |
  |---|---|---|
  | frontend engine calls | 2 (+1 repair) | 0 |
  | `generate_frontend` | 3 s fake (real engine: minutes per page) | 0 s |
  | frontend lane (validate + its preview) | 55 s + 54 s after a repair | 55 s, no repair |
  | end to end | 139 s | **100 s** (warm Docker cache) |

  The **backend lane now sets the total** (generate + validate + repair + its preview, ~80 s with the fake engine;
  with a real engine its CLI calls dominate — 17.6). Found on the way: right after `make up` the preview images
  build from a cold Docker cache (frontend ~106 s, backend ~49 s, built one after the other), so the first run took
  226 s; preview image builds are the next thing to speed up once the engine time is gone.
- Verified: `make test` with every sandbox test (`BGA_SANDBOX_TESTS=1`, 442 passed), including the rendered tracker
  on mocks (forms test submits both forms) and the full dynamic flow with the live switch and live smoke; `make up`:
  COMPLETED, switched to the live backend, every page rendered with live data and no page errors.
