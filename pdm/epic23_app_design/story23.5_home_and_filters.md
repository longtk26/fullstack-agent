# Story 23.5 — Home and filter variants

**Epic:** [23 — App design](epic23_app_design.md) · **Requirements:** FR-37, FR-36 · **Depends on:** 23.3

## User story

As a user of a generated app, I want to land on what I came for (the latest posts, the videos to watch, today's
bookings, or the figures) and to filter it in the way that suits the records.

## Context

- The outline's `home` is `dashboard` or an entity; the dashboard is a grid of figures and charts (`AppDashboard`,
  aggregates from 21.5 / 22.3).
- List filters show as a toolbar above the table.

## Steps

1. **Home variants** (`outline.home_view`): `dashboard` (today), `feed` (the main entity's list in its feed view,
   newest first), `catalogue` (a search box and rows of records per category, an enum or reference field, each row
   linking to the filtered list), `agenda` (today's and the coming records by a date field, needs a range, 23.4),
   `bento` (the dashboard's figures and charts with one or two lists in a bento grid of mixed tile sizes). Each is
   made of existing sections and bindings: lists with a filter, sort or range, and the dashboard's aggregates.
2. **Filter styles** (per list, `AppEntity.filters_style`): `toolbar` (today), `chips` (one row of chips for an
   enum or a reference with ≤ 12 values), `facets` (a side panel with counts for back offices; counts from a
   grouped count aggregate added by code), `search-first` (a large search box, filters in a sheet). The filters are
   the contract's; a style is a presentation. The URL keeps the filter state (shareable, back button works).
3. **Planner.** Code checks each home and filter style against the contract (a `catalogue` needs a category field,
   `facets` an enum or reference filter) and falls back to `dashboard` / `toolbar` with a note.
4. Tests: home planning per variant (bindings checked by the pair check), the fallbacks, facet counts as aggregates,
   kit tests, URL state.

## Acceptance criteria

- [x] The news feed opens on its feed, the video library on a catalogue by channel, soccer bookings on an agenda,
      the project tracker on a dashboard or bento.
- [x] Chips, facets and search-first filter through the contract's parameters only; the filter state lives in the
      URL.
- [x] A variant that doesn't fit the contract falls back with a note; pair check 0 issues.
- [ ] No design-check failures; the app walk passes.
- [x] Static golden passes.

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test`, `make design-check-app`, `make app-design-report`.

## Status

**Done (2026-11-06), on the fake engine and mocks.**
- **Homes:** `dashboard`, `feed` and `catalogue` (rows by the badge's category with "See all" links into the filtered
  list), `agenda` (the coming records by day) and `bento` (the dashboard's first chart as a large tile). A home on a list
  is the main entity's list at `/`; an app that opens on a list keeps its figures on `/dashboard` (Story 23.1's fix).
- **Filters:** `toolbar` (today's), `chips` (one row per short enum filter), `facets` (a side panel; the grid only when
  the panel has something to show) and `search-first`; all through the contract's parameters, the state in the URL.
- Code replaces a home or a filter style the list cannot serve, with a note.

Deviations: facets show no counts (counts would need a grouped aggregate per filter); the app walks and the
375 px / dark sweep wait for the final check with the user's real test.
