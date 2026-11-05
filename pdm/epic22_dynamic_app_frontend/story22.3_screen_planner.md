# Story 22.3 — Screens from the contract

**Epic:** [22 — Dynamic app frontend](epic22_dynamic_app_frontend.md) · **Requirements:** FR-36, FR-32, FR-35 · **Depends on:** 22.2, 10.0b

## User story

As a user of a generated app, I want every thing the API can do on a screen where I expect it: a list per entity, a
detail page with its children, forms for create and edit, actions for custom operations, and a dashboard.

## Steps

1. **Screen planner** (`orchestrator/frontend/app/screens.py`, pure, no model): from the contract, the plan and the
   outline, write FrontendSpec pages of app sections:

   | Contract | Screen |
   |---|---|
   | `list` | `/<plural>`: `AppList` with the list's search, filters and sort; row actions view, edit, delete |
   | `get` | `/<plural>/[id]`: `AppDetail` with the detail fields; a tab per child entity with its list and "Add" |
   | `create` / `update` | `/<plural>/new`, `/<plural>/[id]/edit`: `AppForm`; a child's create from its parent's tab takes the parent from the route (`x-bga.source: route`, 10.0b) |
   | `delete` | a row and detail action with a confirm dialog |
   | custom operation on a record (`card.review`) | an `AppActions` button on the detail (and row, when it has no body); a body opens a dialog with an `AppForm` on its request schema |
   | custom operation on a collection (`card.listDue`) | a list view of its own (`/<plural>/due`) linked from the nav or the parent |
   | aggregate (21.5) | figures and charts on the dashboard and on the parent's detail |

   Each section the planner writes carries its full binding, as FrontendSpec sections do today: the operation id,
   its parameters (`$route.id`, `$record.id`), the fields shown, and for forms each field with its source (10.0b). The
   spec is the record of what calls what; the renderer turns it into code with no engine, and a spec edit (Epic 16)
   is re-checked by the pair check.
2. **Navigation**: the outline's `nav`, then every entity with a `list` and no parent; children are reached from the
   parent's detail.
3. **Coverage by construction**: `uncovered_operations` (19.7) returns nothing for an app spec; an operation the
   planner cannot place (no fitting shape) is noted in `unresolved` with the reason. The Manage area is not added.
4. **Pair check**: the planner's output passes `check_spec_pair`, including `FE_FIELD_SOURCE` (10.0b).

## Acceptance criteria

- [x] For flashcards, project-tracker, shop and book club: every contract operation is on a screen or an action, and
      the planner's notes list nothing unplaced (tests per example).
- [x] A child created from its parent's detail tab needs no parent input; from its own list page it gets a picker
      (22.6).
- [x] The draft carries no bindings; every binding in the spec is written by the planner and passes the pair check.
- [x] The planner is deterministic (same input, same pages); snapshot tests per example.
- [x] Static golden passes.

## Verify

`make lint`, `make test ARGS=tests/test_app_screens.py`, then `make test`.

## Status

**Done (2026-11-05).** `frontend/app/screens.py` (`app_frontend_spec`, pure): from the completed outline, the
BackendSpec and the contract it writes pages, forms and every binding, with one binding per section (a parent's page
lists each child in its own `AppList` with `content.tab`; the dashboard has one `AppDashboard` per figure), so
`check_spec_pair` and `uncovered_operations` check all of them. `ensure_aggregates` turns the outline's dashboard into
BackendSpec aggregate operations (templated like CRUD; the BackendSpec's own aggregates are reused, and any the
dashboard does not name join it). Navigation: the outline's entities, then custom lists of their own, then any list
no page links to. The Manage area is never added (`integration/nodes.py` skips it for app specs). Tests:
`tests/test_app_screens.py` (flashcards, two-entity / project tracker, shop, task-management: every operation placed,
no pair issue at all, snapshots in `tests/fixtures/app-screens/`; the plugin specs of Epic 10's tests plan too).

Live check (Antigravity, a new requirement "Bike Shed", 2026-11-05): SUCCEEDED with one call and no repair; BackendSpec,
FrontendSpec and pair valid with no warnings, nothing unplaced; the model used `dateField` for "spent this year".
252 s in 21 agent turns (~730k input tokens): Antigravity's agent loop, not the planner. Kept as
`tests/fixtures/drafts/bike-shed-antigravity/` and replayed in the tests. Seen for 22.4: "cost per bike" groups by
`bikeId`, so the chart must label bars with the bikes' names; the code-picked direction gave this family app a
monospace font (JetBrains Mono): direction picking is unchanged by this epic, worth a look.

Deviations:
- No book club example exists in `examples/`; task-management, the plugin specs and the two live drafts stand in.
- A child whose parent has a page is created from that page only (parent from the route, hidden); its own list has no
  "New" button until pickers (22.6). A child whose list does not filter by its parent (a cart item) gets an "Add …"
  link on the parent's page instead of a tab. A second required parent is typed as an id (an `FE_FIELD_SOURCE`
  warning and an unresolved note) until 22.6.
- An update without a `get` gets an edit page that starts empty (a partial update).
- Figures and charts are on the dashboard only, not on the parent's detail page.
