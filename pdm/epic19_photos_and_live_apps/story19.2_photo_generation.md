# Story 19.2 — Photo generation with the Gemini image API

**Epic:** [19 — Real photos and API-driven dynamic apps](epic19_photos_and_live_apps.md) · **Requirements:** FR-31 · **Depends on:** 19.1, 18.7

## User story

As a user, I want every photo in my site generated in seconds while the rest of the frontend is built, cached so
the same photo is never paid for twice, and replaced by a placeholder when it cannot be made.

**Scope after the 2026-10-31 decision:** drafts make their photos while drafting and store them as uploads (19.3),
so this story's generation-time path serves (a) `source: "photo"` in specs written or imported by hand, and (b)
regenerable photos (upload assets with a `prompt`, 19.1) whose upload is gone. The generator, the post-processing,
the cache and the records built here are **shared** with 19.3: build them as reusable functions, not inside
`generate_assets`.

## Context

- `generate_assets` (`orchestrator/frontend_assets.py`) already runs in parallel with `generate_frontend`
  (Story 18.7) and draws SVGs with one engine call per drawing. Photos go into the same node, **not** through the
  code engine: a direct HTTP call from the worker.
- Pillow 13 and httpx are installed. `modules/uploads/infrastructure/adapters/image_processor.py` already decodes,
  strips metadata and re-encodes images (`MAX_PIXELS` guard).
- `model_calls` rows need a `cli_invocation_id` (not null), so image calls get their own record.
- The worker that runs a generation may be the container worker or the host worker (`ANTIGRAVITY_AUTH=account`);
  both need the key in their environment.

## Steps

1. **Probe (needs the user's yes: one real image, ~$0.03).** A throwaway script in the scratch directory calls the
   API as documented (see the epic: `POST /v1beta/interactions`, `gemini-3.1-flash-lite-image`, `1K`, `16:9`,
   `image/jpeg`) with a food prompt. Record in a new `docs/engines/gemini-images.md`: the exact request and
   response shape, the latency, the image size in bytes and pixels, and what a blocked prompt returns (try one
   harmless prompt the docs say is refused, e.g. a real public figure's likeness, only if the user agrees). If
   the documented call does not work, find the working one in the docs and record it; do not guess.
2. **Package `agent-api/src/images/`** (like `src/sandbox`, `src/preview`):
   - `port.py`: `IImageGenerator` with `async generate(prompt: str, aspect_ratio: str) -> GeneratedImage`
     (`data: bytes`, `mime`, `model`, `duration_ms`, `cost_usd`); errors `ImageBlocked(reason)` and
     `ImageFailed(reason)`.
   - `gemini.py`: `GeminiImageGenerator` over httpx (timeout from settings, one retry on 429/5xx with backoff, no
     retry on a block). Never log the key; redact it from errors.
   - `fake.py`: `FakeImageGenerator` returning a small deterministic PNG (colour from a hash of the prompt). Mark
     it and list it in `docs/development/test-doubles.md`.
   - a factory from settings; `None` when photos are off or no key is set.
3. **Settings** (`config.py`, `.env.example`):
   - `image_provider: Literal["gemini", "fake", "none"] = "gemini"`
   - `gemini_image_api_key: str | None = None` (falls back to `GEMINI_API_KEY` when empty)
   - `gemini_image_model: str = "gemini-3.1-flash-lite-image"`, `gemini_image_size: str = "1K"`
   - `gemini_image_price_usd: float = 0.0336`, `image_concurrency: int = 4`, `image_timeout_seconds: int = 60`
   Pass the key to the host worker too (`make` targets that start it) and to the compose worker.
4. **Prompt text.** Built in code, not by the engine: `<prompt>. <style>. Photorealistic photograph. No text,
   letters, logos or watermarks in the image.` Trim to 1 000 characters. The prompt comes from the user's spec:
   send it only to the image API, never into a shell or a file name.
5. **Post-processing.** Decode with Pillow (reuse the guards of `image_processor.py`), crop to the exact aspect
   ratio if needed, scale to at most 1 600 px on the long side, encode **WebP** (quality ~80), strip metadata.
   Write `public/assets/<id>.webp`; set `width`, `height`, `sha256`, `generated: True` on the plan asset.
6. **Cache.** `ARTIFACT_ROOT/asset-cache/photos/<key>.webp`, key = sha256 of model, prompt text (step 4),
   aspect ratio, size, and a `PHOTO_VERSION` constant. A hit copies the file and costs nothing.
7. **In `generate_assets`:** photos run concurrently with the SVG drawings, under their own semaphore
   (`IMAGE_CONCURRENCY`; they do not take engine slots). Plan writes go through the plan lock from 18.7. Events:
   `frontend.photo.ready` (`id`, `cached`, `durationMs`), `frontend.photo.fallback` (`id`, `reason`).
   No generator (no key / `none`) → every photo stays a placeholder with reason "photos are off (no
   GEMINI_IMAGE_API_KEY)".
7a. **Missing uploads.** Today `copy_uploads` (`scaffold_frontend`) leaves an asset whose upload is gone as a
   placeholder. For an upload asset that has a `prompt` (a regenerable photo), `generate_assets` makes it again
   as a photo (same prompt, style and aspect ratio; the cache usually has it) instead, with an event
   `frontend.photo.remade` (`id`, `upload`). User uploads without a prompt stay placeholders as today.
8. **Records.** New table `image_calls` (`id`, `generation_id` nullable, `draft_id` nullable, `node_run_id`,
   `asset_id`, `model`, `status` ok | cached | blocked | failed, `duration_ms`, `cost_usd`, `error`, `created_at`;
   exactly one of `generation_id` / `draft_id` is set) with its migration, entity, repository and store method.
   A tracing span per photo (`image:<asset id>`) through `orchestrator/tracing.py`. `/usage` reports
   `images: {count, cached, costUsd}` per generation, per draft (next to the draft's engine usage) and in totals;
   the UI's usage view shows it.
9. **Generation status.** A photo fallback is a warning: the run ends COMPLETED_WITH_WARNINGS as it does for
   `asset_fallbacks` today.
10. Tests (fake generator): concurrency limit; cache hit (no call, `cached` row); blocked → placeholder + warning;
    no key → placeholders, no calls; WebP output with the right aspect ratio; the usage numbers; the key never
    appears in logs or records (test with a sentinel key); a regenerable photo whose upload was deleted is remade,
    a user upload without a prompt is not.

## Acceptance criteria

- [x] Probe findings recorded in `docs/engines/gemini-images.md`.
- [x] Photos are generated in `generate_assets`, in parallel, at most `IMAGE_CONCURRENCY` at a time, as WebP
      files the site serves.
- [x] Cached photos are reused without a call; blocked or failed photos fall back with a warning.
- [x] Every call is recorded (`image_calls`), traced, and counted in `/usage` with its cost.
- [x] Without a key, generations work exactly as before (placeholders, a clear reason).
- [x] A regenerable photo whose upload is gone is remade during generation.
- [x] Generator, post-processing, cache and records are reusable by drafting (19.3).
- [x] Fake generator listed in `docs/development/test-doubles.md`.

## Status

Implemented 2026-10-31:
- Probe executed against Generative Language Interactions API with `gemini-3.1-flash-lite-image` at 1K, 16:9 JPEG; findings documented in `docs/engines/gemini-images.md`.
- Created package `agent-api/src/images/` with `port.py`, `gemini.py` (redacting keys), `fake.py` (test double with triggers), `factory.py`, `prompt.py`, `post_process.py` (Pillow WebP q80), `cache.py`, and `service.py`.
- Added migration `b2d6f8a4c1e3_epic19_photos.py` creating `image_calls` table and adding `origin` and `prompt` columns to `uploads`.
- Integrated `image_calls` recording into `ExecutionRecordRepository`, `JobStore`, and `/usage` rollup reporting.
- Updated `generate_assets` in `frontend_assets.py` to generate photos concurrently with drawings, handle caching, remake missing regenerable upload assets, and report fallbacks.
- Unit tests added in `tests/test_photo_generation.py`.

## Verify

`make lint`, `make test`, `make up` with the fake engine and `IMAGE_PROVIDER=fake`: a static generation of
`examples/frontend-specs/static-landing.json` with one asset switched to `photo` shows the fake photo in the
preview.
