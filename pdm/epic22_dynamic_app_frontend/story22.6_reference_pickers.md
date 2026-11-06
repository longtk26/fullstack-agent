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
   With the picker in place it becomes an error (10.0b made it a warning while forms had no picker).
5. **A list for every referenced parent:** when `x-bga.ref.listOperation` is `null`, the draft's pair fixes add the
   parent's `list` operation to the BackendSpec (deferred from 10.0b, step 4).

## Acceptance criteria

- [x] No app form in the examples (`flashcards`, `project-tracker`, `shop`, book club, `workshop-bookings`) shows an
      id input.
- [x] A child created on its parent's page takes the parent from the route; elsewhere the parent is picked by its
      label.
- [x] Lists and details show parents by label, on mocks and live.
- [x] Agent tests for each source and for the picker's generated code.
- [x] Static golden passes.

## Verify

`make lint`, `make test`; `make up`, generate `flashcards-dynamic` with the fake engine and add a card from a deck's
page and from the cards page.

## Status

**Done (2026-11-06).** Fields by source (`screens.form_fields`): `server`, `currentUser` and `upload` are not shown
(uploads come with 22.7); a parent the page knows is a hidden field with `$route.id`; any other reference, on create
and edit forms alike (moving a card to another deck), gets a `reference` (app-only `FormField.reference`: the parent's
`list`, its `get`, the label field, `q` when the list has search, a page size within the list's `maxLimit`); `input`
fields are the 22.5 components. The kit's `form/ReferenceField.tsx` is a combobox (Popover + Command): it loads the
first 50 records, searches on the server with `q` when the list has search (else cmdk filters them in the browser),
shows the label, sends the id, and loads a chosen record missing from the first page through the parent's `get`; a
clear button when optional. Readable references were in place from 22.4 (`FieldValue`: the `{id, label}` summary as
a link; the mocks present the same summaries); a parent without a label now shows as its kind, never the id.
`FE_FIELD_SOURCE` is an error for app specs (a warning still in the legacy flow, which has no picker).
`screens.parent_lists` (run first in `ensure_aggregates`, so the draft writes it into the BackendSpec) adds a
paginated `list` searched on the label to each referenced parent without one.

Verified: `tests/test_app_pickers.py` (no id input in any example app or the venue fixture, each source, the route
vs the picker, the added parent list, the picker's code, readable references, the schema) and the updated
`test_app_screens.py`; the kit sandbox build; full suite; lint. Live (`make up`, fake engine, `DYNAMIC_FRONTEND=app`): the project tracker and flashcards
COMPLETED with every check (221 s, 210 s); the app walk passed 12/12 and 17/17 (it now picks a parent on each edit
form: a card moved to another deck, a task to another project), and a card's edit form shows its deck by name with
the decks listed. `make design-check-app` on the venue fixture (the booking edit form now has a venue picker): its new
`clipped` metric found the date-time row widening the 375 px column past the card's edge (the card hid it, so the
page did not scroll); fields now shrink (`min-w-0`), and all 16 form views pass.

Deviations: the examples named in the criteria include a book club and `workshop-bookings`, which are not in the repo;
the check runs on the four example apps (`flashcards`, `project-tracker`, `shop`, `task-management`) and the venue
fixture. The parent list is added by the app flow's `ensure_aggregates`, not by `pair_fixes` (the legacy flow keeps
its forms as they are until 22.8 removes it).
