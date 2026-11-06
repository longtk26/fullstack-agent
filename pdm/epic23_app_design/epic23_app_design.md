# Epic 23 — App design: layouts that fit the data, looks to choose from, areas per role

## Overview

Proposed 2026-11-06, after Epic 22, for the user's review. Epic 22 made dynamic apps work: one draft call, every
screen built by code from the contract on one shadcn app kit, every operation reachable, forms that fit the API, and
the plugin frontends. Apps now integrate with their backend correctly. **But they all look alike.** Two causes:
one layout for every app (Epic 22's D2), and a theme limited to colours, fonts, radius and density (D3).

This epic keeps the part that makes apps correct: code still writes every binding, so the pair check, the mocks,
the scenarios and the live switch keep working. It changes **how the same sections are presented**. The model
chooses from a fixed **design space**: archetype, shell, a view per entity, field roles, home and filter styles, and
a style recipe. Code checks each choice against the contract and builds it from kit variants. Apps whose users see
different products (a learner's catalogue and a manager's back office) get one **area** per role group.

Static mode does not change (static golden test). Each story starts with any backend or contract work it needs
(the user's order: the backend decides, the frontend only reads).

| Finding (code, 2026-11-06) | Effect |
|---|---|
| `AppPage.tsx` has one layout (`mx-auto max-w-6xl`, a 4-column figures grid, tabs for children); `AppShell.tsx` is always the shadcn sidebar | A video library, a news feed and an admin console get the same frame |
| `AppList.tsx` shows a table, or cards when `listStyle === "cards"`. Those two are the only list views | Media, feeds, boards and calendars all become tables |
| `drafting/app.py` `app_theme` keeps style, colours, fonts, radius, density and direction only; surface, colour area, motion and icon style are dropped (D3) | Epic 20's look axes never reach apps |
| `design_direction.py` `STYLE_PRESETS` flattens a UI UX Pro Max style (Glassmorphism, Neubrutalism, …) to one of five presets | The data names the right style, but nothing renders it |
| The outline has no field roles: which field is the image, the title, the meta line, the badge | A card can't put the cover on top and the price below |
| Contract list filters are equality only (`filters`, `sort`, `q`, `limit` / `offset`) | A calendar or a "this week" view can't ask for a date range |
| One shell for all roles; Story 22.7 hides what a role can't use | A learner gets the manager's back office with fewer items |
| `fonts.py` holds 30 Latin-only families; kit strings are English only | A Japanese app shows kana in the device's font and English buttons |

**Requirements:** FR-37 (new, proposed: app design space, style recipes, areas per role), FR-36, FR-33, FR-22.
Research: the user's reference screenshots (2026-11-06: a developer news feed, an LMS admin console, a video
library); the 32-style survey the user shared; `frontend-generation-flow.md` at the workspace root.

## Decisions (proposed 2026-11-06)

| # | Decision | Instead of |
|---|---|---|
| D1 | **Choose from a design space, never draw a layout.** The model picks enumerated values (archetype, shell, a view per entity, field roles, home, filters, recipe). Code checks them against the contract and falls back to a default it notes. Refines Epic 22's D2 | Free layouts per page; one layout for every app |
| D2 | **Bindings don't change.** Every new view presents an existing app section (`AppList` → table / cards / media grid / feed / board / calendar; `AppDetail` → record / media / profile). Sections, operations and parameters are what the planner writes today | New sections with their own bindings |
| D3 | **Layout follows the data; the look offers choices.** One layout per area (the right view for the records). Three looks (style recipes) to choose from, checked by a difference test. The layout can be changed in the review as a spec edit | Three layouts to choose from |
| D4 | **Styles are recipes in the kit**: tokens plus CSS for surfaces, backdrop, borders, shadows, motion and icon style, each with accessibility fallbacks (contrast AA on the real composite, reduced motion, reduced transparency). Lifts Epic 22's D3 limit for apps | Model-written CSS; five presets |
| D5 | **One draft call stays.** The design brief is part of `draft_app`'s structured answer (`design` in the outline); candidates come from code (UI UX Pro Max rows, recipes allowed for the product). Draft time ≤ +20% | A second model call for design |
| D6 | **The brief runs before the contract.** A view may need list features (a date range for a calendar, a larger page for a board), so code applies the brief to the BackendSpec between `complete_outline` and `ensure_aggregates`, before `build_contract` | Views asking for data the API doesn't serve |
| D7 | **The backend decides visibility.** An area never filters records in the browser. "Learners see only published courses" is a backend rule (23.9) that the contract, the mocks and the scenarios carry | Frontend filtering per area |
| D8 | **No engine call in the frontend lane by default** (Epic 22's D5 stays). Engine-written view slots (23.11) are an opt-in experiment behind a flag, with the kit as fallback | Turning the engine on for every app |
| D9 | **Measure first.** An app design report with a baseline from today's kit (23.1), run again at each checkpoint | Judging by eye |

## The design space

What the model may choose, per app or per area. Code owns the meaning of each value.

| Axis | Values | Needs from the contract |
|---|---|---|
| Archetype | `back-office`, `catalogue`, `feed`, `workspace`, `booking`, `learning`, `storefront` | sets the defaults below |
| Shell | `sidebar`, `topbar`, `topbar-tabs`, `rail`; mobile: `drawer` or `bottom-tabs` | — |
| Entity view (list) | `table`, `cards`, `media-grid`, `feed`, `board`, `calendar` | board: a status flow with transitions; calendar: a date field and a date-range filter; feed: a date sort |
| Entity view (detail) | `record`, `media`, `profile` | media: an image field |
| Field roles | `media`, `title`, `subtitle`, `meta`, `badge`, `stat`, `price`, `avatar` | the field exists and has a fitting type |
| Home | `dashboard`, `feed`, `catalogue`, `agenda`, `bento` | feed / catalogue: a list; agenda: a date field |
| Filters | `toolbar`, `chips`, `facets`, `search-first` | chips / facets: enum or reference filters on the list |
| Density | `compact`, `comfortable`, `spacious` | — |
| Look | a style recipe (23.7) plus colours and fonts | — |

## What the prototype changed (Story 23.0, 2026-11-06)

Seven real Gemini drafts (news feed, video library, learning platform, agency projects, dental clinic, plant shop,
event tickets) were built on the kit with a prototype overlay. The user reviewed them and said go. What it changed:

| Finding | Where it lands |
|---|---|
| The brief's layout choices fit the data in all seven; the model chose areas on its own for three | the design space stays as planned |
| The seven requirements and their recorded drafts are the golden apps, and the sample requirements per product type | 23.1 (`examples/requirements/`, `examples/specs/`, `examples/app-outlines/`) |
| Gemini wrote `entities` as an object and `meta` as a string, against the answer schema | 23.6 accepts both shapes and records whether the schema was used |
| UI UX Pro Max's ranking matched "video library" to a component library | 23.6 adds archetype keywords before the ranking |
| A field used for two roles (category as subtitle and badge) | 23.3 keeps the first role |
| Only safe looks (minimal, swiss, editorial) in all seven | 23.7 passes the product type's styles from the data, the user's style words win, and the three looks span a range |
| The kit reads one list style per entity for the whole app | 23.10 carries views per area |
| Attendees saw the organizers' revenue dashboard | 23.9 also guards aggregates by role, and `draft_app` learns it |

## Stories

A gate (23.0, done) and five checkpoints. Stop for the user's review after each checkpoint.

| Checkpoint | # | Story | Depends on |
|---|---|---|---|
| **Gate** | 23.0 | [Prototype harness: see the epic's output before building it](story23.0_prototype_harness.md) | Epic 22 |
| **A: measure and frame** | 23.1 | [App design report and baseline](story23.1_app_design_report.md) | Epic 22 |
| | 23.2 | [Shells and page frames](story23.2_shells_and_frames.md) | 23.1 |
| **B: views that fit the data** | 23.3 | [Field roles and entity views](story23.3_entity_views.md) | 23.2 |
| | 23.4 | [Board and calendar views, with date-range lists](story23.4_board_and_calendar.md) | 23.3 |
| | 23.5 | [Home and filter variants](story23.5_home_and_filters.md) | 23.3 |
| **C: the brief and the look** | 23.6 | [The design brief in the draft](story23.6_design_brief.md) | 23.2–23.5 |
| | 23.7 | [Style recipes and three looks](story23.7_style_recipes.md) | 23.6 |
| | 23.8 | [Japanese and English typesetting for apps](story23.8_app_typesetting.md) | 23.7 |
| **D: areas per role** | 23.9 | [Visibility rules (backend)](story23.9_visibility_rules.md) | Epic 10 |
| | 23.10 | [Areas: a different app per role group](story23.10_areas.md) | 23.6, 23.9 |
| **E: beyond the kit** | 23.11 | [Engine-written view slots (opt-in experiment)](story23.11_view_slots.md) | 23.10 |
| | 23.12 | [Final check and acceptance](story23.12_final_check.md) | 23.1–23.10 (23.11 if run) |

23.9 is backend only and can start at any time, in parallel with Checkpoints A–C.

## The flow after this epic

```
requirement ──(one API call, draft_app@v3)──▶ BackendSpec + outline + design brief
                                                  │
  code: complete_outline → apply_design (23.6: check the brief, add list features: date ranges, sorts, page sizes)
        → ensure_aggregates → build_contract → app_theme (recipe tokens, 23.7) → app_frontend_spec
          (screens per area, 23.10; the same bindings, a `view` per section)
                                                  │
                                                  ▼
          kit: shell variant per area, view variants per section, recipe CSS ──▶ renderer (no engine)
                                                  │
                                 build, typecheck, scenarios, preview on mocks, then live (unchanged)
```

## Measures

Set the baselines in 23.1 and run again at each checkpoint.

| Measure | How | Target |
|---|---|---|
| Apps differ | greyscale first-screen similarity at 1440 px between the golden apps' home pages and main lists | home: max ≤ 0.90, mean ≤ 0.70; main list: max ≤ 0.90 (baseline 23.1: home mean 0.742, max 0.980; list mean 0.759, max 0.991) |
| Distinct frames | distinct (shell, home, main list view) triples across the golden apps | ≥ 6 of 8 (baseline: 3, all on the sidebar) |
| Looks within a draft | the difference test on the three looks | 100% pass |
| Fit | views the brief chose that code had to replace | ≤ 1 per app; each one noted |
| Quality floor | `make design-check-app` at 375 / 1440 px, light / dark, every recipe, every area | no failures |
| Integration | pair check, scenarios on mocks, the app walk, the live switch | unchanged: 0 pair issues, every scenario that passes today still passes |
| Cost | draft time and calls (`spec_drafts`), frontend lane engine calls | one draft call, ≤ +20% draft time; 0 engine calls in the lane (unless 23.11 is on) |
| Static | `tests/test_static_golden.py` | byte for byte unchanged |

## Epic acceptance

- The golden apps of 23.1 (including the three reference products: a news feed, an LMS with a learner and a manager
  area, a video library) draft in one call and render with frames and views that fit their data, on mocks and live.
- Every draft offers three looks that pass the difference test; picking one in the review changes the theme only.
- A Japanese requirement drafts a Japanese app: Japanese labels, kit strings, dates and a bundled Japanese face.
- The LMS app shows learners a catalogue they may only read and enrol in, and managers a back office; the backend
  hides drafts from learners (proved by the scenarios, on mocks and live).
- Epic 22's guarantees hold: every operation reachable, no id inputs, 0 pair issues, static golden unchanged.
- The user reviews screenshots of the golden apps (light and dark, 375 and 1440 px) against the 23.1 baseline and
  accepts.

## Not in this epic

- Static sites (Epics 20–21, 20.10's static part).
- Computed fields (the booking form's `startsAt` / `amount`, 22.8's open note) and a full parent's "full" state
  (22.7's deviation): backend changes for an Epic 10 follow-up.
- Illustrations, 3D, parallax and scroll storytelling (Tier 3 of the style survey): app landing pages keep Epic 22's
  `AppLanding`.
- Revisions after generation (Epic 16): until then, changing the look after Generate means generating the frontend
  again.
- A map view (needs a map provider and geodata in the BackendSpec).

## Status

**Implemented (2026-11-06) on `feat/epic23-app-design`, on the fake engine; the real tests and the user's review are
next.** The gate (23.0) made ten real Gemini drafts ($0.50, the golden apps); Stories 23.1–23.12 made no paid call (the
user's instruction). Every story's Status lists what was verified and what waits for the real test; 23.12 has the
numbers (distinct frames 3 → 6 of 8; the greyscale similarity target is not met and does not fit apps).

Found and fixed on the way: an app opening on a list left its figures without a screen (23.1); a parent's foreign key
may title a record (23.3); **the planner ignored every policy on an aggregate** (23.9, from Epic 21); Japanese faces in
`FONTS` leaked into a static pairing (23.8, caught by the static golden).
