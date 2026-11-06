# Story 23.12 — Final check and acceptance

**Epic:** [23 — App design](epic23_app_design.md) · **Requirements:** FR-37 · **Depends on:** 23.1–23.10 (23.11 if run)

## User story

As the user, I want to see the golden apps side by side against the baseline, with the numbers, before I accept
the new app design flow.

## Steps

1. Run `make app-design-report` on the golden apps and compare with 23.1's baseline and the epic's targets.
2. Screenshots for review: each golden app's home and main list, every area, light and dark, 375 and 1440 px, in its
   first look and its two alternatives; a contact sheet against the baseline's.
3. Integration: on the fake engine, every golden app COMPLETED with 0 pair issues, its scenarios on MSW, the app walk
   per area on mocks and live; workshop bookings' plugin walk in both token modes.
4. Cost: draft time and calls per golden app; frontend lane engine calls (0 without 23.11).
5. One real draft-and-generate run (Gemini API draft, templated backend) on the LMS requirement, only with the
   user's yes.
6. Update `pdm/README.md` (epic table, status, decisions), `requirements.md` (FR-37, a version note) and
   `frontend-generation-flow.md` and its diagram (the design brief between `complete_outline` and
   `ensure_aggregates`, areas, recipes).

## Acceptance criteria

- [ ] The report meets the epic's targets, or the user accepts the gap.
- [x] Epic 22's guarantees still hold on every golden app; static golden unchanged.
- [ ] The user reviews the screenshots and accepts.
- [x] README, requirements and the flow doc are updated.

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test`, `make up`, `make app-design-report`.

## Status

**Implemented and checked on the fake engine (2026-11-06); the user's real test and review are next.** No Gemini or
real-engine call was made in Stories 23.1–23.12 (the user's instruction); the gate (23.0) made ten real drafts ($0.50).

Final report (`make app-design-report`, `.data/reports/app-design/2026-11-06/`), against the baseline of 23.1:

| Measure | Baseline (today's kit) | After Epic 23 | Target |
|---|---|---|---|
| Distinct frames (shell, home, main view) | 3 of 8, all sidebar | **6 of 8** | ≥ 6 ✓ |
| Home similarity (greyscale first screen) | mean 0.742, max 0.980 | mean 0.735, max 0.973 | mean ≤ 0.70, max ≤ 0.90 ✗ |
| Main list similarity | mean 0.759, max 0.991 | mean 0.733, max 0.971 | max ≤ 0.90 ✗ |
| Design-check failures (1440 px light) | 0 | 0 | 0 ✓ |
| Frontend engine calls | 0 | 0 (slots off) | 0 ✓ |
| Static golden | — | rendered files unchanged (base files refreshed, 23.8) | ✓ |

Frames now: agency projects a sidebar with a **board**; the clinic an **agenda** home and a **calendar**; event
tickets, the plant shop and the video library a **top bar catalogue** with **media grids**; the news feed a top bar
**feed**; Learnly a sidebar with a media grid; workshop bookings unchanged (no brief). Variants: the clinic and the news
feed built as Japanese apps, the video library and event tickets with the fake engine's view slots: 0 failures each.

**The similarity measure does not fit apps.** Epic 20's "squint" compares 64×40 greyscale first screens: for apps on
light themes it scores the masses of white, not the layout; and the screenshots are signed out, so the clinic's home
(secured) is its sign-in page, which scores 0.973 against workshop bookings' dashboard. The structural measure
(distinct frames) moved from 3 to 6 of 8. Proposed for the real test: signed-in screenshots per area (the prototype
harness already signs in as each demo user), in the looks the user picks, and the user's review instead of the
greyscale target.

Epic 22's guarantees hold on every golden app: every operation on a screen (areas included), 0 pair issues, no form
asks for an id (`tests/test_app_screens.py`, `tests/test_app_areas.py`). Full suite: 1150 passed (sandbox tests not
run); ruff, eslint and tsc clean.

**Real test, 2026-11-06 (Lumen, a photo portfolio):** the Gemini draft seeded the cover photos as Unsplash links;
the smoke seed uploaded each seeded file value as an object key and the store refused `https://…` (`PutObject
InvalidArgument`), so no smoke call ran. Fixed in the storage plugin: a seed's outside `http(s)` link is kept on the
record and read as it is (`signed_url`, the mocks' `fileUrls`); the smoke seed uploads, and the scenarios send, the key
code would have given that row (`outside_url`, `_stand_in`). Uploads still take keys only (`check_upload`). An image
that does not load shows the placeholder (`Media`) or the empty value (`FileValue`). `tests/test_storage.py`.
Second run: `favourite.create (success)` got 409 `DUPLICATE` from `uniqueTogether (ownerId, seriesId)`, where the
server sets `ownerId`: the scenario compared the pair without the owner and sent the series the default demo user had
already favourited. The contract now fills a server-set owner with the scenario user's seeded id (`_caller_id`), picks
a series that user has not, and the duplicate repeats one of that user's own pairs (`tests/test_concurrency_rules.py`).

Open for the real test (each needs paid calls, a live backend or the browser):
- real `draft_app@v3` drafts of the seven golden requirements and a Japanese one (one call each, ~$0.05);
- live backends: range filters, visibility rules, guarded figures, the smoke scenarios (`BGA_SANDBOX_TESTS=1`);
- the app walks per area and the sign-in redirect; the 375 px / dark / twelve-recipe design sweep;
- a real-engine run of the view slots, then the user's decision on keeping them.
