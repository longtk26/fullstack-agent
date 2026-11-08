# Story 27.1 — The Unsplash photo provider

**Epic:** [27 — Stock photos from Unsplash](epic27_stock_photos.md) · **Requirements:** FR-41

## User story

As the agent, I want to turn "a photo of <subject>" into a real Unsplash photo with its credit, so generated sites
and apps show real photos without paid image generation.

## Steps

1. `IMAGE_PROVIDER=unsplash` (`UNSPLASH_ACCESS_KEY`; the app id and secret key are not needed for public search).
2. Search: `GET https://api.unsplash.com/search/photos` (`Authorization: Client-ID <key>`, `Accept-Version: v1`)
   with the photo's search phrase, `orientation` from the asset's aspect ratio (landscape / portrait / squarish),
   `content_filter=high`; the first result not already used in the same project.
3. The result: `urls.raw` with `w`, `h`, `fit=crop` for the asset's size, the photographer's name and profile link,
   the photo page, its colour (placeholder background) and alt description.
4. When the photo is used, `GET links.download_location` once (Unsplash's download tracking).
5. Cache phrase + orientation → photo; count requests against the hourly limit (`X-Ratelimit-Remaining`); out of
   requests or no result → the asset falls back as today (placeholder), with the reason recorded.
6. Tests with a fake Unsplash API (no network): orientation, sizing parameters, no duplicates, cache, download
   tracking once, fallback on 403 / empty results.

## Acceptance criteria

- [x] A photo asset resolves to an images.unsplash.com URL and a credit, without downloading the image.
- [x] A repeated phrase costs no request; a used photo is tracked once.
- [x] Out of requests or no result, the asset falls back with its reason, and the draft still succeeds.

## Verify

`make lint`, `make test`, the key check (one real search).

## Status

**Implemented (2026-11-08); the real check is Story 27.3.** `src/images/unsplash.py` (`UnsplashPhotos`, `StockPhoto`,
`orientation`, `size_for`), `IMAGE_PROVIDER=unsplash` with `UNSPLASH_ACCESS_KEY` / `UNSPLASH_APP_NAME`
(`get_stock_photos`; `photos_enabled` counts it). A search keeps ten results per phrase and orientation, so another
photo for the same phrase costs nothing; 403 / 429 / a remaining count of 0 stop the searching for the instance. Tests
on httpx's MockTransport (`tests/test_unsplash_photos.py`). The three criteria above are met in tests; the real key
is used in 27.3.
