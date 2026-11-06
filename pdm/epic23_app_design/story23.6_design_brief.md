# Story 23.6 — The design brief in the draft

**Epic:** [23 — App design](epic23_app_design.md) · **Requirements:** FR-37, FR-24, FR-36 · **Depends on:** 23.2–23.5

## User story

As a user describing an app, I want the draft to choose a frame, views and a home that fit my product, from the
same single draft call, so that a video library and an invoicing tool no longer look the same.

## Context

- Until this story, code picks the archetype from the UI UX Pro Max product row (23.2) and views from the types.
- `draft_app@v2` answers in a structured schema (`drafting/answer_schema.py` `app_answer_schema`, 22.8).
- Order in `drafting/app.py` today: `complete_outline` → `ensure_aggregates` → `build_contract` → `app_theme` →
  `app_frontend_spec` → `check_draft`.

## Steps

1. **Candidates (code, before the call).** From the requirement, `design_direction.py`'s ranked product rows give
   1–3 archetype candidates and the recipes the product allows (`styles.csv` "Best For" / "Do Not Use For",
   `products.csv` "Primary / Secondary Style", "Dashboard Style"). They go into the prompt's fact pack as the
   choices, not as the answer.
2. **`draft_app@v3`.** The outline gains `design`: `archetype`, `shell` (optional, else the archetype's), `home_view`,
   and per entity `view`, `detail_view`, `roles`, `filters_style`, plus `looks`: three recipe names with a one-line
   reason each (23.7 builds them). All are enums in the answer schema, so the model can't invent a value. The prompt
   explains each value with when to use it ("board when records move through statuses"), and that the layout must
   follow the data, not the product's popularity.
3. **`apply_design` (code, pure, `frontend/app/design.py`)**, between `complete_outline` and `ensure_aggregates`:
   check every choice against the BackendSpec (fields, types, status flows, date fields); add the list features the
   views need to the BackendSpec (date ranges for calendar / agenda, a date sort for feed, grouped counts for
   facets); replace what doesn't fit with the archetype's default and add a note to the draft (`DESIGN_REPLACED`,
   with the reason). Then the contract is built from the updated BackendSpec as today.
4. **Review.** The draft review shows the brief in plain words ("Catalogue, top bar; videos as a media grid; home: by
   channel") with a selector per value (the same enums); a change is a spec edit and runs `apply_design` and the
   planner again (no model call).
5. **Fake engine.** Its recorded drafts gain a `design`; drafts without one (old fixtures) get code defaults, so
   every test keeps working.
6. Tests: answer schema with `design`, `apply_design` per rule and per fallback, BackendSpec additions before the
   contract, prompt snapshot `tests/fixtures/prompts/draft_app.v3{,.inline}.md`, review edits.

## Acceptance criteria

- [ ] One draft call per app; the answer has a `design` that validates against the schema.
- [ ] Every choice that doesn't fit the contract is replaced by code with a note; the report's "replaced views" is ≤ 1
      per golden app.
- [x] Views that need list features get them in the BackendSpec before the contract; the pair check has 0 issues.
- [ ] The user can change any design value in the review without a model call.
- [ ] Draft time ≤ +20% of 22.8's (82 s for soccer bookings on the Gemini API).
- [x] Static golden passes.

## Verify

`make lint`, `make test`, `make up` with the fake engine on the golden apps, `make app-design-report`. One real draft
per golden requirement on the Gemini API only with the user's yes (about $0.06 each).

## Status

**Implemented (2026-11-06); the real-draft criteria wait for the user's real test (no Gemini call in this epic).**
- **`draft_app@v3`** (`prompts/draft_app/v3.md`): v2 plus the design brief, areas, the visibility rule (23.9) and the
  locale (23.8); code's archetype candidates (`archetype_candidates`: the requirement's words, then the ranked product
  types), the data's recommended looks and the requirement's style words in the context; two design examples (the
  golden news feed and event tickets outlines). Prompt snapshots `tests/fixtures/prompts/draft_app.v3{,.inline}.md`.
  v2 and its snapshots are unchanged (its digest and schema leave the design out: `outline_schema(design=False)`).
- **Answer schema** with `design` and `areas` (`app_answer_schema(..., design=True)`); code reads Gemini's other shapes
  too (entities as an object, `meta` as a string: Story 23.0).
- **Structured output recorded:** `EngineResult.structured` (None: no schema asked; False: the API refused the schema)
  and `usage.calls[].structured` on the draft (22.8's open question).
- **`apply_design`** is `complete_design` (Story 23.2) inside `complete_outline`; the list features before the contract
  (`list_features` inside `ensure_aggregates`).
- **Review:** the editor's **App design** card (agent-ui `AppDesignPanel`): pick one of the three looks, the shell and
  each list's view, as spec edits (`lib/app-design.ts`), no model call; the draft summary shows the brief in one line.

Deviations: the home view is not editable in the review (it changes the pages: a new draft or a later revision); the
golden drafts have 1–3 replacements each (a field in two roles, a parent as a title before the fix, roles that do not
fit), more than the ≤ 1 aimed at; draft time and one-call checks need real drafts.
