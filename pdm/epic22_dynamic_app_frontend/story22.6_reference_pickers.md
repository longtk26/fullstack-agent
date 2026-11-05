# Story 22.6 — Reference pickers and readable references

**Epic:** [22 — Dynamic app frontend](epic22_dynamic_app_frontend.md) · **Requirements:** FR-35, FR-36 · **Depends on:** 22.5, 10.0b

The frontend half of 10.0b. Epic 10 puts the sources in the contract (`x-bga.source`, `x-bga.ref`) and the parent
summaries in the responses; this story uses them.

## User story

As a user of a generated app, I never type an id: a form fills in what the page or the signed-in user already knows,
and lets me pick a related record by its name; lists and details show related records by name.

## Steps

1. **Fields by source** in `AppForm`:

   | `x-bga.source` | In the form |
   |---|---|
   | `server`, `currentUser` | not shown |
   | `route` | not shown; the value comes from the route parameter |
   | `reference` | picker (below) |
   | `upload` | upload field (22.7) |
   | `input` | the 22.5 component for its type |

2. **Reference picker**: a Combobox (Popover + Command) on `x-bga.ref.listOperation`, searching with `q` when the list
   has search, else the first 50 records filtered in the browser; shows `labelField`, sends the id; with a route
   parent fixed, it is not shown.
3. **Readable references**: `AppList` and `AppDetail` show the parent summary (`deck.name`) as a link to the parent's
   detail, never the id; MSW mocks and fixtures carry the same summaries (from the contract's examples).
4. **`FE_FIELD_SOURCE`** (pair check, 10.0b) runs on app specs too; the planner (22.3) only writes forms it passes.

## Acceptance criteria

- [ ] No app form in the examples (`flashcards`, `project-tracker`, `shop`, book club, `workshop-bookings`) shows an
      id input.
- [ ] A child created on its parent's page takes the parent from the route; elsewhere the parent is picked by its
      label.
- [ ] Lists and details show parents by label, on mocks and live.
- [ ] Agent tests for each source and for the picker's generated code.
- [ ] Static golden passes.

## Verify

`make lint`, `make test`; `make up`, generate `flashcards-dynamic` with the fake engine and add a card from a deck's
page and from the cards page.

## Status

**Planned (2026-11-05)**, split from 10.0b.
