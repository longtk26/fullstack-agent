# Story 19.3 — Photos made while drafting, stored as uploads

**Epic:** [19 — Real photos and API-driven dynamic apps](epic19_photos_and_live_apps.md) · **Requirements:** FR-31 · **Depends on:** 19.2, 12.6, 15.4

## User story

As a user, I want a drafted site (static or dynamic) to come with its real photos already made, matching the design
direction, so that I can see them, regenerate or replace one in the review, and the generation does not wait for
them or pay for them again.

## Context

- Drafting: `orchestrator/drafting.py` (`DraftRunner._run`: draft call → `apply_design` → `draw_images` → checks →
  repair loop → save). `draw_images` turns placeholder images into `source: "generate"` SVGs with the chosen
  direction's style. Static and dynamic drafts share this runner.
- Design direction: `orchestrator/design_direction.py`, mirrored by `agent-ui/lib/design-direction.ts`.
- Draft prompt: `prompts/draft_frontend_spec/v5.md` (latest).
- Uploads (Story 15.4): `modules/uploads` (`UploadEntity`: `id`, `owner_id`, `filename`, `mime`, `bytes`, `width`,
  `height`, `sha256`; files under `UPLOAD_ROOT`; the same content uploaded twice is one upload); referenced from a
  spec as `upload:<id>`; copied to `public/assets/` by `scaffold_frontend` (`copy_uploads`).
- Retention: `JobStore.prune_uploads` deletes uploads older than `UPLOAD_RETENTION_DAYS` (30) that **no saved
  FrontendSpec** uses (`UploadRepository.unreferenced_before`). Drafts are not counted today.
- 19.2 provides the generator, post-processing (WebP), cache and `image_calls` records.

## Steps

1. **Is it on?** `photos_enabled()` = an image generator exists (19.2 factory). Pass it to the draft prompt context
   and keep it on the draft so the review knows.
2. **Prompt `draft_frontend_spec/v6.md`** (copy of v5) adds, only when photos are enabled: "An image of a real-world
   subject (food, places, people at work, products, nature, culture, events) is `source: "photo"` with a `prompt`
   that names the subject, the setting, the light and the framing, e.g. 'a steaming bowl of pho on a street stall
   table, morning light, close-up, shallow depth of field'. Illustrations, logos, patterns and icons stay as they
   are. Never write image URLs. At most N photos (N from settings); give them to the images that matter most (hero,
   key records)." Switch `drafting.py` to v6.
3. **Photo style from the design direction.** Each direction gets a `photoStyle` (e.g. warm minimal → "warm natural
   light, soft shadows, muted tones"; bold playful → "bright saturated colours, high contrast"), derived from the
   direction's existing fields in `design_direction.py` and mirrored in `lib/design-direction.ts`. A photo without a
   `style` gets the direction's `photoStyle`.
4. **`draw_images` rule.** Remaining placeholder `image` assets become photos when photos are enabled and the cap
   allows, otherwise SVG drawings as today. Assumption notes say what was converted and why.
5. **Make the photos at the end of the draft.** After the repair loop (the spec is final), in `DraftRunner._run`,
   with `progress="photos"`: for every `source: "photo"` asset, in parallel (`IMAGE_CONCURRENCY`), call the shared
   generator (19.2: same prompt text, post-processing and cache), store the WebP as an **upload** owned by the
   draft's owner, and rewrite the asset to `"source": "upload:<id>"`, keeping `prompt` and `style` (a regenerable
   photo, 19.1). Then re-run `check_draft` (nothing should change; it guards the rewrite).
   - A blocked or failed photo keeps `source: "photo"` (generation tries again, 19.2) with an assumption note
     giving the reason.
   - Record each call in `image_calls` with `draft_id`; the draft's usage shows `images: {count, cached, costUsd}`.
   - Uploads get two new columns: `origin` (`user` | `photo`, default `user`) and `prompt` (text, nullable); the
     uploads list in the UI labels photo uploads "AI photo".
6. **Keep draft photos.** `unreferenced_before` also counts references from drafts that still exist
   (`spec_drafts.frontend_spec`, any status), so an unsubmitted draft does not lose its photos after 30 days. A
   deleted draft releases them. Add a test.
7. **Regenerate and replace in the review.**
   - `POST /api/v1/spec-drafts/{id}/assets/{assetId}/regenerate` (optional body `{prompt?, style?}`): owner only
     (others → 404, `ensure_owner`); makes a new photo with the shared generator (synchronous, timeout
     `IMAGE_TIMEOUT_SECONDS`), stores it as a new upload, updates the asset in the draft's `frontend_spec`
     (source and prompt), records the call on the draft, returns the updated asset. Errors use `ErrorCode`
     (`IMAGE_BLOCKED`, `IMAGE_FAILED`, `PHOTOS_DISABLED`). The API container needs `GEMINI_IMAGE_API_KEY` too (check
     `docker-compose` env for the `api` service).
   - Replace: the existing upload flow (15.4) already lets the user upload a file; the review offers "Replace with my
     own image" on a photo, which sets `upload:<new id>` and drops the `prompt`.
   - The review shows each photo (thumbnail from the upload), its prompt (editable before regenerating), the site's
     photo cost so far and the estimate for a regeneration (`GEMINI_IMAGE_PRICE_USD`, from an API field, not
     hard-coded). When photos are off: "AI photos are off: set GEMINI_IMAGE_API_KEY".
8. **Both modes.** Static and dynamic drafts run the same code. Imported sites (`source: "frontend"`, BackendSpec
   only) do not make photos.
9. **Golden example** `examples/frontend-specs/street-food-static.json`: a static food and culture site with 3–4
   page photos (hero, a market scene, a cooking scene) as `source: "photo"` and a `dishes` collection (used in
   19.4). It must validate; the UI's examples list serves it. (An example has no uploads; its photos are made during
   generation, which also exercises 19.2.)
10. Tests (fake generator): v6 prompt snapshot (enabled / disabled); `photoStyle` per preset (Python, plus a UI unit
    test if the UI has them); `draw_images` with photos on and off and the cap; end of draft: photos become uploads
    with prompts, a failed one stays `photo` with a note, `image_calls` rows carry `draft_id`; retention with a
    draft reference; the regenerate endpoint (owner, other user → 404, photos off → error, blocked → error and the
    asset unchanged).

## Acceptance criteria

- [x] With a key, static and dynamic drafts end with their photos made and stored as uploads; the spec holds
      `upload:<id>` with the prompt.
- [x] A photo that could not be made stays `source: "photo"` with a note, so generation retries it.
- [x] Without a key, drafts behave as before (drawings and placeholders).
- [x] Photo style follows the chosen design direction, identically in Python and the UI.
- [x] The review shows the photos, regenerates one (with an edited prompt) or replaces it with an upload.
- [x] Draft photo uploads are not pruned while their draft exists.
- [x] Draft usage includes the photo calls and their cost.
- [x] `street-food-static.json` added and valid.

## Verify

`make lint`, `make test`, `cd agent-ui && pnpm exec tsc --noEmit && pnpm lint`, `make up` with the fake engine and
`IMAGE_PROVIDER=fake`: a static and a dynamic fake draft end with photo uploads; regenerate one in the review;
generate the draft and check the generation makes **no** image calls (`image_calls` has no rows for it) and the
preview shows the photos. Record the time of `generate_assets` with photos in the spec compared with the same spec
using `source: "photo"`.
