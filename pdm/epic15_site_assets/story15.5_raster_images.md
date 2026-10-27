# Story 15.5 — AI raster images (optional)

**Epic:** [15 — Site images & illustrations](epic15_site_assets.md) · **Requirements:** FR-28 · **Depends on:** 15.3, 8.2

## User story

As a user who wants photo-like pictures and accepts the cost, I want the agent to generate them with an image
model, opt-in per generation.

> Optional. SVG illustrations (15.2) and uploads (15.4) cover most sites; build this only if users ask for it.

## Acceptance criteria

- [ ] `kind: "photo"` with `source: "generate"` (15.1 accepts it once this story lands).
- [ ] Port `IImageProvider.generate(prompt, aspect_ratio, style) → bytes` with adapters chosen by
      `IMAGE_PROVIDER`: `none` (default), `gemini`, `openai`; each reads its own key from the environment
      (`GEMINI_API_KEY` is reused when set). A fake provider returns fixed images for tests (listed in
      `docs/development/test-doubles.md`).
- [ ] Off unless the generation sets `options.frontend.rasterImages: true` **and** a provider is configured;
      otherwise photo assets get warning `FE_IMAGE_PROVIDER_UNAVAILABLE` and stay placeholders.
- [ ] Called by the worker inside `generate_assets`, never from the sandbox. Output normalised with Pillow to WebP,
      longest side ≤ 1 920 px, ≤ 500 KB, written to `public/assets/<id>.webp` (owned).
- [ ] Cached like 15.2; each image is a model call with its cost (provider price table) in usage and traces.
- [ ] The UI shows the estimated cost before submit; the manifest marks these assets `generatedBy: <provider/model>`.
- [ ] Tests with the fake provider: opt-in off → placeholder; on → file written, cached on re-run, cost recorded.
