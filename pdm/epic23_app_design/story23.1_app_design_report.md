# Story 23.1 — App design report and baseline

**Epic:** [23 — App design](epic23_app_design.md) · **Requirements:** FR-37 · **Depends on:** Epic 22

## User story

As the team, we want to measure how alike generated apps look before we change the kit, so that "more varied" and
"still correct" can be checked at every checkpoint instead of judged by eye.

## Context

- Epic 20's diversity report (`make design-diversity`, `scripts/design_diversity.py`) measures static sites only.
- `make design-check-app` (Story 22.4) screenshots an app's screens at 375 / 1440 px, light and dark, on its mock
  API. `scripts/app-walk.mjs` and `plugin-walk.mjs` prove the screens work.

## Steps

1. **Golden apps.** Eight requirements in `agent-api/tests/fixtures/app-golden/`, each with a recorded draft (fake
   engine replays it, no paid call):
   - the existing ones: flashcards, project tracker, corner shop, workshop bookings, soccer pitch bookings (22.8);
   - three new ones, matching the user's reference screenshots: a developer news feed (posts with cover, source,
     tags, upvotes), an LMS with learners and managers (courses, lessons, enrolments; learners only see published
     courses), a video library (videos with thumbnail, channel, views, duration).
2. **Report** (`make app-design-report`, `scripts/app_design_report.py`): for each golden app, render on mocks and
   take the home page and the main list page at 1440 px, light. Measure:
   - greyscale first-screen similarity between every pair of apps (mean and max);
   - the (shell, home, main list view) triple per app, and how many are distinct;
   - the views the brief chose that code replaced (0 today, since there is no brief);
   - design-check failures at 375 / 1440 px, light / dark;
   - draft time and calls (from the recorded draft), frontend lane engine calls.
   It writes `.data/reports/app-design/<date>/report.md` and a contact sheet PNG of all home pages.
3. **Baseline.** Run it on `main` today and store the numbers in this story's Status and in
   `tests/fixtures/app-golden/baseline.json`; the targets in the epic's Measures are confirmed or adjusted with the
   user here.
4. Tests: the report on two fixture apps (fake renders, deterministic numbers), the similarity function.

## Acceptance criteria

- [ ] Eight golden app requirements with recorded drafts replay on the fake engine with no paid call.
- [ ] The report gives similarity, distinct frames, replaced views, design-check failures and cost per app.
- [ ] The baseline is recorded; the user confirms the epic's targets.
- [ ] Static golden passes.

## Verify

`make lint`, `make test ARGS=tests/test_app_design_report.py`, `make up`, then `make app-design-report`.

## Status

**Done (2026-11-06).** No model call: the golden apps are Story 23.0's seven real Gemini drafts plus Epic 22's
workshop bookings.
- **Sample requirements and golden apps:** `examples/requirements/{news-feed,video-library,learning-platform,
  agency-projects,clinic-bookings,plant-shop,event-tickets}.md` (in the UI's "Load example"), their drafts as
  `examples/specs/<name>.json` + `examples/app-outlines/<name>.json`, the briefs and recorded costs in
  `agent-api/tests/fixtures/app-golden/<name>/`. The fake engine replays them by keyword (`GOLDEN_APPS` in
  `fake_engine.py`, checked first: the ticketing requirement mentions "workshops"); `docs/development/test-doubles.md`
  updated.
- **Report:** `scripts/app_design_report.py`, `make app-design-report [ARGS="--app … --baseline"]`: plans each golden
  app as `draft_app` does (the requirement's first direction for the theme), builds it on mocks, screenshots home and
  main list at 1440 px light, and writes `report.md`, `report.json` and `contact-sheet.png` under
  `.data/reports/app-design/<date>/`. App rules for the quality floor (`app_failures`: sideways scroll, web fonts not
  loaded, more than two families, form problems); marketing rules (type sizes, CTA) do not apply to app screens.
- **Baseline** (today's kit, `tests/fixtures/app-golden/baseline.json`): home similarity mean 0.742, max 0.980 (news
  feed / workshop bookings); main list mean 0.759, max 0.991; 3 distinct frames of 8, all on the sidebar; 0 failures.
  The epic's targets were set from it (home max ≤ 0.90, mean ≤ 0.70; list max ≤ 0.90; ≥ 6 distinct frames).
- **Found by the golden apps (fixed):** an app whose home is a list left its dashboard figures without a screen
  (`channel.count`, `appointment.countByStatus` unused); the planner now adds a `/dashboard` page and nav item when the
  outline has figures (`screens.build`).
- Tests: `tests/test_app_design_report.py` (helpers, every golden app plans), the golden apps in
  `tests/test_app_screens.py` (every operation placed, 0 pair issues, snapshots).

Deviations: eight golden apps, not the planned mix (three existing examples were replaced by Story 23.0's real
drafts); no draft time measured beyond the recorded ones (no paid calls in this epic, per the user).
