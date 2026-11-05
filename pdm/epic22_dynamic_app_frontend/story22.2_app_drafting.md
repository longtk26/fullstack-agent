# Story 22.2 — Drafting a dynamic app

**Epic:** [22 — Dynamic app frontend](epic22_dynamic_app_frontend.md) · **Requirements:** FR-36, FR-24 · **Depends on:** 22.1

## User story

As a user, I want a dynamic app drafted in about a minute and a half, with the model deciding what the app is
(entities, navigation, labels, figures) and not how each page is laid out.

## Problem

The dynamic draft asks the model for full FrontendSpec pages and then for a tree per page; in the book club run
(2026-11-05) that was 8 calls and 4 min 16 s, and most of the output was layout.

## Steps

1. **App outline** (FrontendSpec `app`, additive, dynamic only):

   | Field | What |
   |---|---|
   | `name`, `tagline`, `icon` | the app's name and Lucide icon |
   | `nav[]` | `{entity, label, icon}` in order; entities left out are reached from their parent |
   | `home` | `dashboard` (figures and recent records) or an entity's list |
   | `entities.<Entity>` | `label`, `plural`, `displayField`, `listFields` (≤ 5), `listStyle` (`table` / `cards`), `detailFields` order, `fieldLabels`, `help` |
   | `dashboard[]` | figures: `{label, fn, entity, field, filter, period}` and charts: `{label, kind, entity, fn, field, groupBy}` (aggregates, 21.5) |
   | `landing` | optional: a public first page from library sections (off unless the requirement asks for one) |

   The outline names entities, fields and figures, never operations, routes or parameters: bindings are code's job
   (22.3), so the model cannot bind a screen to the wrong operation or ask for an id.

2. **Prompt `draft_app@v1`**: one call that returns the BackendSpec and the outline; it carries the BackendSpec
   rules from today's draft prompt, the outline schema, and two short examples. No layout, colour or font
   instructions.
3. **Code fills the rest**: defaults for every missing outline field from the BackendSpec (labels from names, the
   display field by 10.0b's rule, list fields: the display field plus the first required fields), and the direction
   from `design_direction.py` (theme only, no model call).
4. **Repair**: validation failures go to `repair_spec` as today; outline errors that code can fix (an unknown field, a
   missing entity) are fixed without a call and noted.
5. **Agent UI**: the draft review shows the outline (navigation, entities, dashboard) instead of page sections for
   app drafts; edits go through the spec editor (9.7a).

## Acceptance criteria

- [x] An app draft makes one model call, plus one repair only when validation fails; no `draft_tree` and no direction
      cards call.
- [ ] Book club, flashcards and project-tracker requirements draft in ≤ 90 s on Gemini Flash (measured with the
      user's yes; the fake engine has an `app` scenario for tests).
- [x] A minimal outline (only `name` and `nav`) and a full one both produce a valid spec pair.
- [x] Prompt snapshot for `draft_app@v1`; schema digest updated; static drafting untouched (static golden passes).

## Verify

`make lint`, the drafting tests, `make test`; `make up`, draft the three requirements on the fake engine and check
the outline in the review.

## Status

**Done (2026-11-05), except the Gemini Flash timing.** `frontend_spec/app.py` holds the outline (`AppOutline`:
`AppNavItem`, `AppEntity`, `AppDashboardItem`, `AppLanding`); `drafting/app.py` makes the one `draft_app@v1` call
(BackendSpec + `app-outline.json`, inputs: the BackendSpec ones plus the outline digest and two examples,
`examples/app-outlines/`), repairs only the BackendSpec, and hands the outline to `frontend/app/outline.py`
(`complete_outline`: labels, plurals, display field, list and detail fields, field labels, list style and navigation
from the BackendSpec and the contract; unknown entities, fields, bad values and impossible figures are dropped with a
note, never repaired by a call). Notes on the outline point into the FrontendSpec (`/app/...`). The fake engine has
an `app` scenario (`APP_OUTLINE_FIXTURES`); the Gemini API engine accepts `draft_app`. The draft review shows the
outline (`AppOutlinePanel`: navigation, entities with their list fields, dashboard) instead of the pages. Tests:
`tests/test_app_drafting.py`.

Live check (Antigravity, `gemini-3.8-flash-medium`, a new requirement "Plant Care", 2026-11-05): the outline was
good (the model's own labels, real fields only, a dashboard answering "how many need water today", a `plant.listDue`
custom operation, four sensible unresolved questions), but the draft ended NEEDS_REVIEW: the BackendSpec had a date
default `today`, and the one `repair_spec` round returned without changing it. Fixed in code
(`fix_backend_defaults`: `today` and the like become `now`, no call) and in the prompt (one line); the run is kept as
`tests/fixtures/drafts/plant-care-antigravity/` and replays to a valid app with a clean pair check. Time: 339 s
(draft 298 s in 16 agent turns, ~450k input tokens, plus a 41 s repair). That is Antigravity's agent loop reading the
input files; the ≤ 90 s target is for the Gemini API engine, still to be measured (with the user's yes).

Deviations:
- `landing` is a small outline of its own (`headline`, `text`, up to three `highlights`, `cta`) rendered by the kit,
  not library sections: library sections belong to the static flow (decision D1).
- Dashboard items take an optional `dateField` (the date a `period` counts; default: the creation timestamp), added
  after the live run, where "needing water today" was counted from the creation date.
- The 15 KB digest limit is checked on the site schema (what the drafting prompts read); the full schema with the
  outline is for the spec editor.
