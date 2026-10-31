# Story 19.1 — `photo` asset source

**Epic:** [19 — Real photos and API-driven dynamic apps](epic19_photos_and_live_apps.md) · **Requirements:** FR-31 · **Depends on:** 15.1

## User story

As a user, I want to mark an image in my FrontendSpec as an AI photo, so that a food, travel or product site shows
real-looking pictures instead of drawings or empty panels.

## Context

- Sources and render modes: `agent-api/src/modules/shared/domain/frontend_spec/assets.py` (`source_kind`,
  `render_mode`, `RenderMode`, `SVG_KINDS`, `MAX_GENERATED_ASSETS`).
- The `Asset` model and its docstring: `frontend_spec/schema_v1.py` (`AssetKind`, `AspectRatio`, `prompt`, `style`).
- Planning: `orchestrator/frontend_planner.py` (the `render_mode` branches near lines 127–150).
- Registry: `orchestrator/asset_registry.py` (`_effective_mode`, `assets_ts`); rendering:
  `templates/nextjs_overlay/files/common/src/components/assets/AssetImage.tsx` (`public-file` → `<img>`).
- Uploads already reach `public/assets/<id>.<ext>` with width, height and hash (`frontend_assets.copy_uploads`).
  Photos reuse the same rendering, but **not** the upload code path (`copy_uploads` reads `asset["upload"]`).

## Steps

1. **Source.** `source: "photo"` is a new source: `source_kind` returns `"photo"`, `render_mode` returns a new mode
   `"photo"` (add it to `RenderMode`). Allowed only for `kind: "image"`; other kinds get
   `FE_UNSUPPORTED_ASSET_SOURCE` with a hint ("photos are for kind 'image'; use 'generate' for illustrations,
   logos and patterns").
2. **Fields.** `prompt` (what the photo shows; defaults to `alt`) and `style` work as for drawings. Update the
   `Asset` docstring and the module docstring of `assets.py`.
2a. **Photos that became uploads.** Drafting turns photos into uploads (19.3): `source: "upload:upl_…"` that
   **keeps** `prompt` and `style`. An upload asset with a `prompt` is a *regenerable photo*: the review can redraw
   it, and generation can remake it when its upload is gone (19.2). Allow `prompt` / `style` on upload assets
   (they are ignored for user uploads without a prompt) and say so in the docstrings. Such assets count towards
   `FRONTEND_MAX_PHOTOS`.
3. **Limit.** `MAX_PHOTOS = 8` with setting `frontend_max_photos: int = 8`; above it the validator warns
   (`FE_TOO_MANY_PHOTOS`, hint: "keep photos for the images a page really needs; the rest stay placeholders").
   Photos do not count towards `MAX_GENERATED_ASSETS` (drawings).
4. **Plan.** In `frontend_planner`, a `photo` asset gets `file: public/assets/<id>.webp`,
   `src: /assets/<id>.webp`, and `generated: False` until 19.2 writes it.
5. **Registry.** In `asset_registry._effective_mode`, a `photo` asset is `"placeholder"` until it has been
   generated, then `"public-file"` with `src`, `width`, `height`. `TAssetMode` in TypeScript does not change
   (photos render exactly like uploads).
6. **Owned files.** Generated photos are generator-owned (`write_registry` in `frontend_assets.py` adds
   `public-file` uploads today: add generated photos the same way).
7. **`frontend:assets` check.** A photo that is still a placeholder (no key, blocked, failed) is a **warning**
   `FE_PHOTO_FALLBACK` with its reason, like `FE_ASSET_FALLBACK`; it never fails the check. A generated photo's
   file must exist and be WebP.
8. JSON Schema snapshot and the 18.9 schema digest updated.
9. Unit tests: validator (photo on `image` ok; on `logo` error; 9 photos warn, counting regenerable uploads),
   planner fields, registry effective mode before/after generation, `frontend:assets` warning, an upload asset
   with a `prompt` validates and plans as a normal upload.

## Acceptance criteria

- [x] `source: "photo"` validates for `kind: "image"` and is rejected with a hint for other kinds.
- [x] More than `FRONTEND_MAX_PHOTOS` photos is a warning, not an error.
- [x] A photo renders as a placeholder until generated, then as a `public-file` image; no change to `AssetImage`.
- [x] `frontend:assets` warns `FE_PHOTO_FALLBACK` for photos left as placeholders.
- [x] Upload assets may keep a `prompt` / `style` (regenerable photos) and count towards the photo cap.
- [x] Existing specs and examples still validate; schema snapshot and digest updated.

## Status

Implemented 2026-10-31:
- Added `source: "photo"` and `"photo"` render mode to `assets.py`.
- Enforced kind `"image"` in `validator.py` with hint to use "generate" for illustrations, logos, patterns.
- `FRONTEND_MAX_PHOTOS` setting (default 8) warns on excess photos including upload assets with prompt.
- Planner sets `public/assets/<id>.webp`, `/assets/<id>.webp`, and `generated: False`.
- Registry sets effective mode to `placeholder` until `generated: True`, then `public-file`.
- `frontend:assets` (`assets_check`) produces `FE_PHOTO_FALLBACK` warning for unbuilt photos and validates generated WebP files.
- Unit tests added in `tests/test_site_assets.py`; FrontendSpec schema digest snapshot updated.

## Verify

`make lint`, `make test`.
