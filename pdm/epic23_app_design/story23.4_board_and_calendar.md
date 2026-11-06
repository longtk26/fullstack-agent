# Story 23.4 — Board and calendar views, with date-range lists

**Epic:** [23 — App design](epic23_app_design.md) · **Requirements:** FR-37, FR-05, FR-36 · **Depends on:** 23.3

## User story

As a user of a generated app, I want tasks on a board I can move between statuses, and bookings on a calendar, so
that the screen matches how I think about the work.

## Context

- A status flow (Epic 10, `transition`) gives a status enum and `transition:<STATE>` in `allowedActions`; Story
  22.7 shows transitions as record actions.
- Contract list filters are equality only (`integration/contract.py`: `filters`, `sort`, `q`, `limit` / `offset`),
  so a calendar can't ask for "this month".

## Steps

Backend and contract first:

1. **Date-range filters.** A BackendSpec list operation may declare `ranges: [{field, param}]` on a date or datetime
   field; the contract adds `<param>From` and `<param>To` query parameters (inclusive, ISO 8601), the backend
   template filters on them, and the smoke check calls each range once. The MSW mocks apply the same range. Code adds
   a range when a calendar view needs one (23.6 applies it before `build_contract`; until then, when the outline
   names `calendar`).
2. **Board lists.** A board lists every record of each status: the list operation gets a filter on the status field
   (already an equality filter) and the board calls it once per column with its own paging ("Load more" per column).
   No new operation.

Then the kit:

3. **Board view** (`view: board`, needs a status flow): a column per state in the flow's order; cards by field roles
   (23.3). Moving a card (drag, or the card's "Move to" menu for keyboard and touch) calls the transition's operation;
   only columns in the card's `allowedActions` accept it; a refusal (409, 403) moves the card back and shows the
   contract message. Without a status flow, code falls back to `cards` with a note.
4. **Calendar view** (`view: calendar`, needs a date field; a second date field for an end): month and week, records
   placed by their dates, a click opens the detail, "New" on a day prefills the date field (`x-bga.source: input`
   with a default). Paged by the visible range through the range parameters. Uses the base's shadcn calendar and
   `date-locale.ts`.
5. **Scenarios.** `scenarios.json` gains a range case per range filter and a transition case per board move; they
   run on MSW and live as today.
6. Tests: the range parameters in the contract and the template filter (backend template tests), the smoke call, MSW
   ranges, board and calendar fallbacks, kit tests for drag and the keyboard menu.

## Acceptance criteria

- [ ] A list with a range filter answers `?startsAtFrom=…&startsAtTo=…` on the live backend and on MSW with the same
      records; the smoke check covers it.
- [ ] The project tracker's tasks show on a board; moving a card calls its transition, and a refused move goes back
      with the server's message.
- [ ] The soccer pitch bookings show on a week calendar, paged by range; a new booking from a day has its date set.
- [x] Board and calendar need no new operation; every operation stays reachable; pair check 0 issues.
- [x] Keyboard and touch users can move cards without dragging.
- [x] Static golden passes.

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test` (template tests and app builds), `make up`, the app walk
on the project tracker and soccer bookings, live.

## Status

**Done (2026-11-06), on the fake engine and mocks; the live backend waits for the user's real test.**
- **Date ranges, backend first:** BackendSpec list operations take `ranges` (date or datetime fields; validated); the
  planner, the router (`<field>From` / `<field>To` query parameters, inclusive), the use case (`<attr>__gte` /
  `__lte` filters) and the repository (a bound-aware filter loop, written only for a module with ranges: every other
  generated file is byte for byte the same) carry them; a `range_<field>` template test; the contract's parameters and
  `x-bga.ranges`; the mocks apply them by name (`entry.ranges`, never by suffix). Code adds a range and a date sort to
  a list shown on a calendar or an agenda (`design.list_features`, before the contract).
- **Kit:** `Board` (a column per state in the flow's order; a card moves through its record menu, the transitions
  `allowedActions` allows; refusals show the contract's message) and `Calendar` (a month on wide screens, the agenda on
  phones; opens on the month of the next record, else the latest; asks the list for the visible weeks through the
  range; previous / next month). Both load up to the list's `maxLimit` at once.
- Verified: `tests/test_list_ranges.py`, the agency board and the clinic calendar on mocks.

Deviations: no drag and drop (moving is the card's menu, which also serves keyboard and touch); a new record from a
calendar day does not prefill its date yet; the range's template test and the live call run with the user's real test
(sandbox template tests were not run in this epic).
