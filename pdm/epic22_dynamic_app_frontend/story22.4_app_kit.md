# Story 22.4 — App kit: shell, lists, details, dashboard

**Epic:** [22 — Dynamic app frontend](epic22_dynamic_app_frontend.md) · **Requirements:** FR-36, FR-25 · **Depends on:** 22.3

## User story

As a user of a generated app, I want it to look and behave like a well-made product: one consistent shell, readable
tables, clear details, loading and empty states, and the same patterns on every screen.

## Steps

1. **Kit components** in `templates/nextjs_overlay/files/dynamic/app/`, built on the shadcn components in the base
   (no new dependencies; tables sort and page on the server, so `@tanstack/react-table` is not needed):

   | Component | What |
   |---|---|
   | `AppShell` | `sidebar` with icons and the outline's nav, collapsible; top bar with breadcrumbs and a slot for the user menu (22.7); a `sheet` on phones |
   | `AppList` | `table` (or cards for `listStyle: cards`) with search, filters, sort and `pagination` bound to the list operation; row actions in a `dropdown-menu`; `empty`, `skeleton` and error states |
   | `AppDetail` | header with the display field and actions; fields in a description grid; `tabs` for children |
   | `AppDashboard` | figure cards and `chart`s from aggregates; recent records |
   | `AppActions` | buttons, confirm `alert-dialog`, `sonner` toasts on success |

2. **One spacing and type scale** for the whole kit (page padding, section gaps, table density from the direction's
   `density`); the direction sets only theme tokens.
3. **Actions from the record:** row and detail actions, and create buttons on a parent, show only what the
   record's `allowedActions` (10.0b) lists; no rule is re-implemented in the frontend. Error messages come from
   `x-bga.errors`, on the field when `fields` is set, else a toast.
4. **Renderer**: app sections render to the kit through the existing contract-bound client and React Query hooks,
   on MSW until the backend is live (as today).
5. **Same behaviour on mocks and live:** the contract's scenarios (10.0b) run against MSW in the Node sandbox
   (`msw/node`, a generated script of seconds, not a test suite; blocking), and after the switch to live through the
   frontend's API path (base URL or proxy), in the background like the other live checks (18.12).
6. **Design checklist**: `DESIGN_CHECKLIST.md` gains an app section (shell, table, detail, states, focus order,
   keyboard use of menus and dialogs); `scripts/design-check.mjs` measures an app fixture at 375 px and 1440 px, light
   and dark.

## Acceptance criteria

- [x] Flashcards and project-tracker render as apps on the kit with no engine call in the frontend lane, build and
      typecheck, and work on mocks and live.
- [x] Every screen has loading, empty and error states; tables page and sort on the server.
- [x] Actions follow `allowedActions` (a record without `delete` shows no delete); errors show their `x-bga.errors`
      message.
- [x] The scenarios pass on MSW and live; a planted mock mismatch fails the frontend lane.
- [x] The app fixture passes the design checklist in light and dark at 375 px and 1440 px.
- [x] Agent tests check the rendered pages for each app section (pytest, no Node).
- [ ] `DYNAMIC_FRONTEND` defaults to `app` once this story is accepted; static golden passes.

## Verify

`make lint`, `pnpm exec tsc --noEmit` (agent-ui), `make test`, `BGA_SANDBOX_TESTS=1 make test` at the checkpoint's
end; `make up`, generate `flashcards-dynamic` and `project-tracker-dynamic` on the fake engine and use them in the
App tab.

## Status

**Done (2026-11-05), except the default switch** (`DYNAMIC_FRONTEND` stays `legacy` until the user accepts this
checkpoint). The kit (`templates/nextjs_overlay/files/dynamic/app/`): `AppShell` (sidebar with the outline's icons,
breadcrumbs, theme switch), `AppPage` (one width and gap; figures in a grid; a parent's children in tabs), `AppList`
(table or cards; search, filters and sort in the URL per section; pages on the server; row actions in a menu; loading,
empty and error states), `AppDetail` (record name as the heading, actions, field grid; `variant: summary`),
`AppForm` (page or dialog; the generated Zod schema; load for edits; server errors on their field, else a toast),
`AppDashboard` (figures; bar, line, area and pie charts, a parent's name for a foreign-key group, a legend for pies),
`AppActions`, `FieldValue` (parents by name and linked, dates in the reader's locale, enums as badges). Data:
`src/content/app.json` from `frontend/app/files.py` (routes, forms, per-entity field types, references, list
operations, the contract's errors, density). Checks: the frontend lane's new `scenarios` check runs the contract's
scenarios against the MSW mocks (`src/mocks/scenarios.test.ts`; the mocks now refuse missing required fields and
unknown parents as the API does); `make design-check-app` (375 / 1440 px, light and dark) and `scripts/app-walk.mjs`
(every screen and action in a browser, from `app.json`). Tests: `tests/test_app_screens.py`, sandbox tests
`test_an_app_on_the_kit_builds_and_renders_on_mocks`, `test_a_planted_mock_mismatch_fails_the_scenarios_check`.

Verified in the real flow (`make up` with `DYNAMIC_FRONTEND=app`): fake-engine generations of the project tracker
and flashcards complete with every check passed (`frontend:scenarios` included), their frontends switch to the live
backend, and the app walk passes every page and action live (open, open a record, edit and save, add a child from
its parent, create, delete from the row menu, record actions). Live check (Antigravity, "Pantry", 2026-11-05):
COMPLETED in 655 s with every check passed; the user's review of it found the bugs below.

Fixed on the way (found by screenshots, the user's review and the app walk):
- **Record links pointed at list pages in generated apps:** the shared FrontendSpec autofix (run when a generation
  attaches its specs) re-checked a link's page without the link's own `params` and re-pointed every link into a
  `[id]` route at the list (view, edit, "Add …"). It now reads the link's params (`frontend_spec/autofix.py`);
  `test_attaching_an_app_spec_changes_none_of_its_links`. Legacy dynamic links with params were affected too.
- **Row deletes never ran:** the confirm dialog lived inside the row menu and closed with it; the chosen row action
  now lives outside the menu (`RowActions` / `ChosenAction`).
- **After "Add task" on a project, the app opened the new task's id as a project:** a form returns to the page whose
  route parameters the current route has, else to the new record.
- **Editing a record with an empty optional field could not be saved** (`null` from the API vs the Zod schema): the
  loaded record's `null`s are dropped.
- **Two figures of one resource shared a React Query cache entry** (a chart showed a figure's value; a custom list
  could show the CRUD list): custom and aggregate GETs have their own keys (`codegen._Operation.query_key`, in
  `bindings.ts` and `queries.ts`).
- **The flashcards fake generation failed `tests` and `openapi` (`deck.count`, `card.count` 404):** the fake engine
  completed those modules by copying hand-written golden files over the templated router and export lists, dropping
  the app flow's aggregate routes. The golden files are now merged into the templated files (`merge_golden`: a
  three-way `git merge-file` against `golden/flashcards_base/`, export lists by name), as an engine's edit would;
  `tests/test_fake_engine_merge.py`.
- **Data tab "Failed to connect":** a preview backend allowed the agent UI only as `localhost`, not `127.0.0.1`; it now
  allows both, and the Data tab says once when the backend preview does not answer (its container stopped).

Deviations:
- `AppForm` is a working form on the operation's request (inputs by type, native date inputs); the full form kit
  (calendar, pickers, validation messages per rule) is Story 22.5 / 22.6.
- The scenarios run on mocks in the frontend lane; live, the same scenarios run in the backend's smoke check (Story
  10.0b). A separate live run through the frontend's API path is not added. Scenarios the mocks cannot answer as the
  API does (conflicts, rules, sign-in) are listed in the check's summary as not emulated, never as passed.
- Seen and not changed here: the code-picked direction gave two family apps monospace headings (JetBrains Mono, Space
  Mono); direction picking is outside this epic's code.
