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

- [ ] An app draft makes one model call, plus one repair only when validation fails; no `draft_tree` and no direction
      cards call.
- [ ] Book club, flashcards and project-tracker requirements draft in ≤ 90 s on Gemini Flash (measured with the
      user's yes; the fake engine has an `app` scenario for tests).
- [ ] A minimal outline (only `name` and `nav`) and a full one both produce a valid spec pair.
- [ ] Prompt snapshot for `draft_app@v1`; schema digest updated; static drafting untouched (static golden passes).

## Verify

`make lint`, the drafting tests, `make test`; `make up`, draft the three requirements on the fake engine and check
the outline in the review.

## Status

**Planned (2026-11-05).**
