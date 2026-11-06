# Story 23.2 — Shells and page frames

**Epic:** [23 — App design](epic23_app_design.md) · **Requirements:** FR-37, FR-36 · **Depends on:** 23.1

## User story

As a user of a generated app, I want the app's frame to suit what it is: a sidebar for a back office, a top bar
with search for a catalogue or a feed, tabs on the phone for an app I use on the go.

## Context

- `AppShell.tsx` is always the shadcn `Sidebar`; `AppPage.tsx` is one frame (`mx-auto max-w-6xl`, `gap-8`).
- Navigation is the outline's `nav`, filtered by role (`canUse`, Story 22.7). This doesn't change.

## Steps

1. **FrontendSpec.** `layout.shell` gains app values: `sidebar` (today), `topbar`, `topbar-tabs`, `rail`, and
   `layout.mobileNav`: `drawer` (today) or `bottom-tabs` (≤ 5 items, else drawer). `layout.frame`: `narrow`
   (reading, `max-w-3xl`), `standard` (today), `wide` (`max-w-screen-2xl`), `full` (boards, calendars). Additive,
   app-only (`_APP_ONLY_PROPERTIES`).
2. **Archetype defaults** (`frontend/app/design.py`, pure): each archetype of the epic's design space maps to a
   shell, mobile nav, frame and density, e.g. `back-office` → sidebar / drawer / standard / compact, `catalogue` →
   topbar with search / bottom-tabs / wide / comfortable, `feed` → topbar-tabs / bottom-tabs / narrow. Until 23.6
   the archetype is picked by code from the UI UX Pro Max product row (`design_direction.py`), never by the model.
3. **Kit.** `AppShell` renders the four shells from the same `nav` and the same user menu (22.7): `topbar` puts the
   nav in the bar and a search box that opens the main list's search (`q`, when the list has search), `rail` shows
   icons only with tooltips. `AppPage` reads the frame. Each shell has its loading, empty and error states.
4. **Checks.** `design-check-app` runs every shell at 375 / 1440 px, light / dark; keyboard navigation and focus
   order checked in every shell; bottom tabs never cover content (safe-area padding).
5. Tests: archetype defaults, the spec fields refused in static mode, kit render tests per shell, snapshot updates
   for the golden apps.

## Acceptance criteria

- [ ] Four shells and two mobile navigations render from the same `nav`; hidden-by-role items stay hidden in each.
- [ ] Each golden app gets the frame of its archetype; the report's distinct-frames count goes up from the baseline.
- [ ] The topbar search searches the main list through the contract's `q`, and is absent when the list has none.
- [ ] No design-check failures in any shell; the app walk passes in each.
- [ ] Static golden passes.

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test` (app builds), `make design-check-app` per shell,
`make app-design-report`.

## Status

**Done (2026-11-06).**
- **The design in the spec:** `AppOutline.design` (`AppDesign`: archetype, shell, mobileNav, frame, density, homeView,
  mainEntity, entities' views and roles, looks, reason, replaced) and `AppOutline.areas` (`AppArea`), app-only (the
  static schema drops them: `DESIGN_DEFS`); not `layout.shell` as planned, so the whole design space lives in one place.
  `draft_app@v2`'s outline digest and answer schema leave them out (`outline_schema(design=False)`), so v2 reads as before.
- **Code completes it** (`frontend/app/design.py`, run by `complete_outline`): archetype defaults (`ARCHETYPES`),
  `archetype_for` (the requirement's words first, then the direction's product type; Story 23.0's ranking miss),
  checks of every value with a note per replacement (`design.replaced`, also draft notes). An outline without a brief
  keeps its own home and list styles; density stays the theme's unless a brief sets it. `draft_app` passes code's
  archetype until the brief names one (23.6).
- **Kit:** `layout.ts` (`useLayout`: the design, with the current area over it; `entityDesign`; `FRAME_WIDTH`);
  `AppShell` renders `sidebar`, `rail` (the sidebar collapsed to icons), `topbar` (sections in the bar, a search over
  the main entity's list `q`) and `topbar-tabs`, all over the role-filtered navigation; phones get bottom tabs (at
  most five sections) or the drawer / a scrolling row; `AppPage` reads the frame. `app.json` gains `design`
  (`kit_design`: today's kit for apps drafted before) and `areas`.
- Verified: `tests/test_app_design.py` (28), the app, form, picker, plugin and static golden suites; builds of the news
  feed (top bar), agency projects (sidebar) and clinic (top bar with tabs) on mocks, 0 design-check failures.

Deviations: the per-shell design-check sweep and keyboard pass run with 23.12's final check.
