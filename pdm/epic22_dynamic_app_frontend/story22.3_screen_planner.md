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

- [ ] For flashcards, project-tracker, shop and book club: every contract operation is on a screen or an action, and
      the planner's notes list nothing unplaced (tests per example).
- [ ] A child created from its parent's detail tab needs no parent input; from its own list page it gets a picker
      (22.6).
- [ ] The draft carries no bindings; every binding in the spec is written by the planner and passes the pair check.
- [ ] The planner is deterministic (same input, same pages); snapshot tests per example.
- [ ] Static golden passes.

## Verify

`make lint`, `make test ARGS=tests/test_app_screens.py`, then `make test`.

## Status

**Planned (2026-11-05).**
