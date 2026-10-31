# Story 19.4 — Photos for records

**Epic:** [19 — Real photos and API-driven dynamic apps](epic19_photos_and_live_apps.md) · **Requirements:** FR-31 · **Depends on:** 19.3

## User story

As a user, I want the records my site shows (dishes, places, products), both static collections and the seed data
of a dynamic app, to come with photos, and records created later to show the image URL they were given.

## Context

- Data sections render image columns with `AssetImage asset={record[field]}`
  (`templates/nextjs_overlay/files/renderer/src/components/sections/CardGrid.tsx:42-44`), so a record's image field
  already holds an asset reference (`asset:<id>`) and the asset comes from the registry.
- Static records: `content` collections in the FrontendSpec. Dynamic records: BackendSpec `seed`, turned into mock
  fixtures by `orchestrator/contract.py` (`build_fixtures`) and into the backend's `seed.json`.
- `AssetImage` renders only registry ids; a URL typed into a form (a record created at runtime) shows a
  placeholder today.

## Steps

1. **Record photos in drafts.** Add this rule to `draft_frontend_spec/v6.md` from 19.3 (it is not released before
   Checkpoint A, so extend it instead of adding a version): for collections and seed records
   with an image field, set the field to `asset:<entity>-<n>` and declare that asset with `source: "photo"`, a
   prompt describing that record (e.g. the dish's name and look), the collection's aspect ratio, and an alt text.
   Photos for records and pages share the cap (`FRONTEND_MAX_PHOTOS`); records beyond it keep a placeholder.
   Record photos are ordinary photo assets, so 19.3 makes them at the end of the draft and stores them as uploads,
   in static collections and dynamic seed data alike; the record keeps `asset:<id>` and only the asset's source
   changes to `upload:<id>`.
2. **Validation.** An `asset:` reference in a collection record or a seed record must name a declared asset
   (`FE_UNKNOWN_ASSET`, existing code). For seed records, check it in the pair check (`checks/consistency.py`) or
   the frontend validator, whichever already resolves records; a BackendSpec image field stays a plain `string`.
3. **Generation.** Record photos are ordinary photo assets: drafted ones arrive as uploads (copied by
   `scaffold_frontend`), hand-written ones as `source: "photo"` (made by 19.2); nothing new in `generate_assets`.
3a. **Dynamic mode: what the API returns.** The backend stores and returns the seed value as it is
   (`"image": "asset:dish-pho"`); the generated frontend turns it into the picture through its registry, on the
   mock API and on the live API. Other API clients (the OpenAPI explorer, a mobile app) see that text, not an
   image. Keep `asset:<id>` (the default) and document it: the generated backend's README
   (`templates/fastapi_overlay/files/README.md`, today only "Run with Docker" / "Run locally") gets a short "Seed
   data" section, written only when the seed has `asset:` values (the README is a template: add a placeholder the
   scaffold fills, as it does for `{{PROJECT_NAME}}`): "Image fields of seed records name frontend assets; the
   generated frontend serves the file at `/assets/<id>.webp`." Switching seed values to frontend paths is a
   possible follow-up, not part of this story.
4. **Runtime URLs.** `AssetImage`: when `asset` is not a registry id but an `https://` URL or a site path
   (`/assets/...`), render it as an image (`remote` treatment for `https://`: `referrerPolicy="no-referrer"`,
   `loading="lazy"`); anything else stays the placeholder. Keep the `data-bga-asset` attribute. Update the
   checklist if it lists `AssetImage` behaviour.
5. **Forms.** A form field for an image field is a URL input (`type: "url"` if the form field types allow it,
   else `string` with a hint in the placeholder). Uploads from the generated site are out of scope.
6. **Golden example.** `street-food-static.json` (19.3) gets its `dishes` collection with 4 records, each with
   a record photo; the flashcards example (19.8) keeps images out (cards have no image field).
7. Tests: validator for unknown record asset refs; `AssetImage` unit test (registry id, https URL, site path,
   junk → placeholder); the fake run of `street-food-static.json` shows the record photos.

## Acceptance criteria

- [x] Drafted collections and seed records with image fields reference photo assets, within the shared cap, and
      those photos are made while drafting (uploads), in static and dynamic mode.
- [x] The generated backend's README explains that seed image fields name frontend assets.
- [x] Unknown asset references in records are reported.
- [x] `AssetImage` renders registry assets, `https://` URLs and site paths; anything else is a placeholder.
- [x] Image fields in forms take a URL.
- [x] `street-food-static.json` shows record photos in a fake run.

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test`, `make up` with the fake engine and `IMAGE_PROVIDER=fake`.

**Checkpoint A after this story:** stop for review. Ask the user before any real image call beyond the 19.2 probe.
