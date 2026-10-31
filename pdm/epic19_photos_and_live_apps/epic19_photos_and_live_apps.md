# Epic 19 — Real photos and dynamic apps driven by their API

## Overview

Two gaps, found on the Anki-style vocabulary run (`gen_01M66QJWJGAZ7WMHZFR6TJ6KMR`, 2026-10-30) and by review:

**1. Sites cannot show real-world pictures.** An asset is a placeholder, an SVG the code engine draws, an upload,
a lucide icon or an `https://` link (`frontend_spec/assets.py`). An SVG cannot show "a bowl of pho" or a temple
festival; food, travel, culture or product sites look empty.

**2. Dynamic apps use their API only partly, and the API lacks the product's behaviour.**

| Finding (measured run) | Effect |
|---|---|
| The UI uses **7 of 13** operations: no edit or delete for cards and decks, review history never shown | It reads like a brochure with a few forms |
| The BackendSpec is **pure CRUD**: `Card` has `intervalDays`, `dueDate`, `repetitionCount`, but no operation schedules a review or lists the cards due | The product's core loop (spaced repetition) is not in the API at all |
| The section library has no edit form that loads a record, no delete or row actions, no filter / search / sort controls, no buttons for custom operations (`Form.tsx`, `DataTable.tsx`, `CardGrid.tsx`) | Even a perfect spec cannot describe an interactive app |
| The mock API answers **501** for every custom operation (`templates/nextjs_overlay/files/dynamic/src/mocks/handlers.ts`) | A UI that calls a domain operation fails its checks on mocks |
| Nothing checks that the UI can do what the requirement asks; the live check is a smoke test of pages | A generation can pass with its main feature missing |

This epic adds AI photos through the Gemini image API, and makes dynamic apps start from the user's journeys:
the journeys bring domain operations into the backend, every operation gets a screen (the journey screens the
drafter designs, the rest in a generated **Manage** area), the section library gains the interactive pieces, and
generated journey tests prove the UI works against the live API.

```
 requirement ─▶ journeys (19.8) ─▶ BackendSpec: CRUD + domain operations (described behaviour)
                     │                        │
                     ▼                        ▼
               FrontendSpec ◀── coverage: Manage area for the rest (19.7)
                     │   interactive sections: row actions, edit forms, list controls, action buttons (19.6)
                     │   photos: page and record images, made while drafting, stored as uploads (19.1–19.4)
                     ▼
 frontend lane: mocks answer custom operations (19.5) ─▶ journey tests on mocks (19.9)
 integrate:     journey tests on the live backend (19.9)
```

**Decisions (user, 2026-10-31):**
- Photos use the Gemini API with **`gemini-3.1-flash-lite-image`** (1K, ~$0.034 per image; the user provides the
  API key). At most **8 photos per site** by default. Without a key, sites keep SVGs and placeholders.
- **Photos are made while drafting**, in static and dynamic mode, and stored as uploads: the spec JSON carries
  `"source": "upload:upl_…"` plus the photo's `prompt`. The review shows the real photos (regenerate or replace
  one before generating), and generation only copies files (Story 15.4 path), so a static site no longer waits for
  photos and a re-generation costs nothing. `source: "photo"` stays for specs written or imported by hand: those
  photos are made during generation (19.2). Image links (`https://…`) remain supported for links the user supplies;
  the drafter never invents them.
- Operations no journey screen uses get **auto-generated** screens (the Manage area); the drafter designs only the
  journey screens.
- One epic, implemented by Gemini, reviewed at the checkpoints.
- **One click** (19.10): the user types a requirement and clicks **Generate**; the spec is drafted and the
  generation starts automatically when the draft is valid. Reviewing the spec first stays available as a choice.

**Facts from the Gemini docs (read 2026-10-31; verify in the 19.2 probe):** image models are the "Nano Banana"
family; Imagen is shut down. `gemini-3.1-flash-lite-image`: 1K only, aspect ratios include 1:1, 3:4, 4:3, 16:9,
21:9 (all of FrontendSpec's), $0.0336 per image, no free tier. The documented call is
`POST https://generativelanguage.googleapis.com/v1beta/interactions` with header `x-goog-api-key` and body
`{"model", "input", "response_format": {"type": "image", "mime_type": "image/jpeg", "aspect_ratio",
"image_size": "1K"}}`; the image comes back base64 in `output_image.data`. Every image carries a SynthID
watermark. The Batch API halves the price but may take up to 24 h, so it is not used.

**Requirements:** add FR-31 (AI photos) and FR-32 (API-driven dynamic apps) to `requirements.md`.

## Stories

| # | Story | Phase | Depends on |
|---|---|---|---|
| 19.1 | [`photo` asset source](story19.1_photo_source.md) | A | 15.1 |
| 19.2 | [Photo generation with the Gemini image API](story19.2_photo_generation.md) | A | 19.1, 18.7 |
| 19.3 | [Photos made while drafting, stored as uploads](story19.3_drafting_photos.md) | A | 19.2, 12.6, 15.4 |
| 19.4 | [Photos for records](story19.4_record_photos.md) | A | 19.3 |
| 19.5 | [Custom operations on the mock API](story19.5_custom_operation_mocks.md) | B | 13.2 |
| 19.6 | [Interactive sections](story19.6_interactive_sections.md) | B | 19.5, 17.4 |
| 19.7 | [Operation coverage and the Manage area](story19.7_manage_area.md) | B | 19.6 |
| 19.8 | [Journeys and domain operations](story19.8_journeys.md) | C | 19.6, 19.7 |
| 19.9 | [Journey tests on mocks and on the live API](story19.9_journey_tests.md) | C | 19.8, 14.2 |
| 19.10 | [One click: from requirement to running app](story19.10_one_click_generate.md) | D | 19.3, 19.8, 2.4, 12.4 |

## How to implement (read first)

Work in this order and **stop at each checkpoint** for review:

1. **Phase A (photos):** 19.1 → 19.2 → 19.3 → 19.4. 19.2 needs one approved real image call (the probe).
   **Checkpoint A.**
2. **Phase B (interactive apps):** 19.5 → 19.6 → 19.7. **Checkpoint B.**
3. **Phase C (journeys):** 19.8 → 19.9. **Checkpoint C.**
4. **Phase D (one click):** 19.10. **Checkpoint D**, then the final check.

Rules (from the repository's `CLAUDE.md`; they apply to every story):

- Branch `feat/epic19-photos-and-live-apps` from `main`. **Do not commit**; the user commits after review.
- Never run paid engines or paid APIs (Antigravity, Claude Code, the Gemini image API) unless a story says so
  **and** the user has said yes in the conversation. Use the fake engine and the fake image generator (19.2)
  everywhere else.
- Every new fake, stub or test-only switch goes into `docs/development/test-doubles.md` and is marked where it is
  defined.
- Prompts are versioned files (`agent-api/prompts/<id>/vN.md`). **Never edit a released version**: add the next
  version and switch the code to it. Latest today: `draft_frontend_spec@v5`, `complete_backend@v1`.
- FrontendSpec and BackendSpec changes are **additive** (new optional fields); existing specs and examples must stay
  valid. Regenerate the JSON Schema snapshots (`UPDATE_SNAPSHOTS=1 make test`) and review the diff. The schema
  digests from 18.9 must include the new fields.
- Overlay files (`agent-api/templates/nextjs_overlay/files/...`) are edited by hand and follow `nextjs-skills`;
  keep `templates/nextjs_overlay/DESIGN_CHECKLIST.md` true (measure with `scripts/design-check.mjs`). Never edit
  `templates/nextjs_base`.
- The UI's `lib/design-direction.ts` mirrors `design_direction.py`: keep both in step.
- New settings go in `src/configs/config.py` with a comment, plus `.env.example`. DB changes: `make newmg`,
  review, plain `varchar` instead of new PostgreSQL enums.
- After each story: `make lint`, `make test`; `BGA_SANDBOX_TESTS=1 make test` when it touches the overlay,
  sandbox or Docker code; `cd agent-ui && pnpm exec tsc --noEmit && pnpm lint` when the UI changes; `make up` with
  the fake engine for the flows the story names.
- After each story, tick its acceptance criteria and add a dated **Status** note (what was done, deviations,
  numbers), as the Epic 18 stories do.

## Golden examples (added in this epic, used by the tests)

- `examples/frontend-specs/street-food-static.json` (19.3): a static food and culture site with page photos and a
  dish collection with record photos.
- `examples/frontend-specs/flashcards-dynamic.json` + `examples/specs/flashcards.json` (19.8): the Anki-style app
  with journeys, domain operations (`card.listDue`, `card.review`, `deck.stats`) and the Manage area.

## Final check (after Checkpoint D, needs the user's yes)

Two real runs with Antigravity and the image key, each started with one click (19.10):
1. The vocabulary requirement ("Create a website help learner to learn vocabulary follow the ankie styling way"),
   dynamic mode.
2. A static food and culture site (e.g. "A website about Vietnamese street food: famous dishes, where to eat them,
   and the culture behind them").

Record in a Status note on this epic: photos generated while drafting, their cost and the draft time they added;
generation time of the static site with its photos already in the spec (no image calls); operations used by the UI (before 7/13,
target: all, journey screens + Manage); journeys passing on mocks and live; total time compared with Epic 18's
final measurement.
