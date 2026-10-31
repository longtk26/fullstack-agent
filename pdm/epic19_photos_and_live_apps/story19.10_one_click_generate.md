# Story 19.10 — One click: from requirement to running app

**Epic:** [19 — Real photos and API-driven dynamic apps](epic19_photos_and_live_apps.md) · **Requirements:** FR-2, FR-32 · **Depends on:** 19.3, 19.8, 2.4, 12.4

## User story

As a user, I want to type my requirement, click **Generate**, and land on the generation page right away, with the
spec drafted and the app generated one after the other without waiting for me, so that the agent works the way an
AI generation app is expected to. Reviewing the spec first stays possible, but it is a choice.

## Context

- Today it takes two steps: `POST /api/v1/spec-drafts` (`specs` module, `CreateSpecDraftUsecase`) queues a draft on
  `bga:drafts:<engine>`; the worker's `_consume_drafts` runs `DraftRunner` (own slots, `DRAFT_CONCURRENCY`) to
  SUCCEEDED / NEEDS_REVIEW / FAILED; the user reviews it and submits `POST /api/v1/generations` with `draftId`
  (`CreateGenerationUsecase._persist`: `_draft`, `_backend_spec`, `_frontend_spec`, then `queue.enqueue`).
- UI: `agent-ui/src/app/(dashboard)/generations/new/page.tsx` → `features/generations/components/NewGenerationView.tsx`,
  the requirement tab `features/specs/components/RequirementTab.tsx`, the draft result `DraftResult.tsx`,
  `store/spec-draft-store.ts`, `features/specs/api/specs-api.ts`.
- `generations.status` is the PostgreSQL enum `generation_status` (`GenerationStatus`); adding a value follows
  migration `9371b02b939f` (`ALTER TYPE ... ADD VALUE IF NOT EXISTS`); its downgrade must rebuild the type (see that
  migration).

## Steps

1. **New statuses.** `GenerationStatus.DRAFTING` (the spec is being drafted) and `GenerationStatus.NEEDS_REVIEW`
   (the draft did not validate; waiting for the user). Both non-terminal. Migration with `ADD VALUE` and a downgrade
   that maps them to `FAILED` and rebuilds the type. Update `StatusBadge` and every switch over statuses (API DTOs,
   filters in the generations list, the UI's status helpers).
2. **API: generate from a requirement.** `POST /api/v1/generations` accepts, instead of specs or `draftId`, a
   requirement: `{"mode", "requirement": {"text", "format"?, "fileName"?}, "options": {...}}`.
   - Validate it with `check_requirement` exactly as `CreateSpecDraftUsecase` does (move the shared part into one
     function; do not copy it).
   - In one transaction: create the draft (`spec_drafts`, new nullable column `generation_id`) and the generation
     (status `DRAFTING`, no spec ids yet, `options.draftId`, `options.autoGenerate: true`, lanes as for the mode).
   - After the commit, queue the **draft** (not the generation) and publish `status.changed` (DRAFTING).
   - Idempotency keys work as today. Backend, static and dynamic modes are all supported; imported sites
     (`source: "frontend"`) keep the review flow.
3. **Shared "attach the draft's specs" step.** Move what `_persist` does with a draft (`_backend_spec`,
   `_frontend_spec`, `_origin`) into one service usable from the API and the worker (e.g. a
   `modules/generations` domain service, or a `JobStore` method that uses the same repositories). It creates the spec
   rows from the draft and links them to the generation.
4. **Worker: chain the draft into the generation.** At the end of `DraftRunner.run`, when the draft has a
   `generation_id` (photos from 19.3 are already made at this point):
   - **SUCCEEDED** → attach the specs (step 3), set the generation `PENDING`, publish `status.changed`, enqueue it
     with `queue.enqueue(generation_id, engine)`. This is the same queue a user submit uses, so slots and engine
     rules stay unchanged.
   - **NEEDS_REVIEW** → the generation becomes `NEEDS_REVIEW` with the draft's errors in the event payload; it waits.
   - **FAILED** (including the pending-timeout reaper) → the generation becomes `FAILED` with code `DRAFT_FAILED` and
     the draft's error.
   - Publish the draft's progress (`drafting`, `validating`, `repairing (n/m)`, `photos`) as `draft.progress`
     events on the **generation's** event stream as well, so the generation page shows it live.
5. **Continue after review.** `POST /api/v1/generations/{id}/continue` with the edited specs (same validation as a
   normal create with `draftId`): only for the owner (others → 404) and only in `NEEDS_REVIEW`; attaches the specs,
   sets `PENDING`, enqueues. Any other status → 409 with an `ErrorCode`.
6. **Cancel while drafting.** `POST /generations/{id}/cancel` in `DRAFTING` or `NEEDS_REVIEW` cancels the
   generation (CANCELLED) and its draft. The draft runner checks a cancel flag (Redis key or the draft row) before
   and after each engine call and before photos, stops the running engine call if the engine port allows it, and
   **never** starts a generation for a cancelled one. Cancelling a queued but unstarted draft removes it from use.
7. **Generation page.** A "Spec" phase before the lanes: draft progress, then the drafted spec read-only (pages,
   entities, journeys, photos, assumptions) with a link to the full draft view. In `NEEDS_REVIEW` the page shows the
   review editor in place, with **Fix and continue**. The usage panel shows the draft's usage (engine and photos)
   next to the generation's, labelled "Drafting".
8. **New generation page.** With a requirement entered, the primary button is **Generate** (step 2, then navigate
   to `/generations/{id}` at once); a secondary option **Draft and review first** keeps today's flow. Generation
   options (engine, preview, Manage area, etc.) are on the same form for both. Remember the last choice per user in
   `localStorage` (convenience only).
9. **Lists and filters.** `DRAFTING` and `NEEDS_REVIEW` generations appear in the generations list with their
   badges; "needs review" is a filter.
10. Tests:
    - API: create from a requirement (draft + generation rows, draft queued, generation not queued); invalid
      requirement → 422; idempotency; continue (owner, other user → 404, wrong status → 409); cancel in DRAFTING.
    - Worker (fake engine): SUCCEEDED → generation PENDING and enqueued, then COMPLETED; NEEDS_REVIEW → waits;
      FAILED → generation FAILED with `DRAFT_FAILED`; cancel during drafting → no generation run; `draft.progress`
      events on the generation stream.
    - Migration up / down.
    - UI: type check, and a component test of the New generation buttons if the UI has component tests.

## Acceptance criteria

- [ ] Typing a requirement and clicking **Generate** opens the generation page at once, in `DRAFTING`.
- [ ] A valid draft starts the generation automatically; the page shows the draft's progress, then the lanes.
- [ ] A draft that needs review stops in `NEEDS_REVIEW`, editable in place, and **Fix and continue** starts it.
- [ ] A failed draft fails the generation with `DRAFT_FAILED` and the draft's error.
- [ ] Cancelling while drafting cancels both; no generation runs afterwards.
- [ ] **Draft and review first** still works as before.
- [ ] Draft usage (engine and photos) is shown on the generation page.

## Verify

`make lint`, `make test`, `cd agent-ui && pnpm exec tsc --noEmit && pnpm lint`, `make up` with the fake engine:
one-click static, dynamic and backend generations COMPLETED; a fake draft forced to NEEDS_REVIEW, fixed and
continued; a cancel during drafting. Record the time from the click to the first lane starting.

**Checkpoint D after this story:** stop for review, then the epic's final check (needs the user's yes), run through
the one-click flow.
