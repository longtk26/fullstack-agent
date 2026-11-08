# Story 31.2 — The Pexels video provider

**Epic:** [31 — Sample videos](epic31_sample_videos.md) · **Requirements:** FR-45 · **Depends on:** 27.1

## User story

As the drafting code, I want to turn a short phrase and a place into a stock video file that fits the place, with its
credit and within the API's limits, so that sites can have moving heroes and apps can seed videos our own player plays.

## Context

- Epic 27's shape: `images/port.py`, `images/unsplash.py` (search, cache, limits), `images/factory.get_stock_photos()`.
- 31.1 adds `videos/port.py` and the YouTube adapter; this story adds the second adapter behind the same port.
- Pexels Videos API: `GET https://api.pexels.com/videos/search` (`query`, `orientation`, `size`, `per_page`), the key in
  the `Authorization` header; each video has `video_files` (link, file type, quality, width, height), `image` (poster),
  `duration`, `user` (name, url) and its page `url`.

## Steps

1. **Terms first (D7):** read the Pexels API terms and guidelines; record here what they require (credit and links,
   hotlinking the files, caching, rate limits and how they are reported in responses) and adjust D3–D5 before writing
   code.
2. **Adapter** `videos/pexels.py` (httpx): search by phrase and orientation (`landscape` for heroes and players,
   `portrait` for phone-first places); keep only MP4 files; choose the smallest file at least as wide as the place
   (1280 px for a hero at most, the card size for seeds), else the largest under it; return the file link, poster,
   size, duration and credit (`Video by <name> on Pexels`, the author's and the video's links).
3. **Limits:** read the remaining requests from the response headers when Pexels sends them, keep a local counter
   otherwise, and stop searching under a margin; errors and limits end the search with no result, never the draft.
4. **Cache:** results by phrase + orientation + minimum width under `ARTIFACT_ROOT/asset-cache/video/pexels/`.
5. **Settings:** `pexels` in `VIDEO_PROVIDERS`, `PEXELS_API_KEY` in `.env.example`; the settings page shows it; a key
   check script like Epic 27's (one search).
6. **Tests:** the adapter against a recorded responder injected from `tests/` (no network): file choice by width, MP4
   only, portrait vs landscape, limits reached, cache hits. The responder is listed in
   `docs/development/test-doubles.md`.

## Acceptance criteria

- [ ] The terms' requirements are recorded in this Status and reflected in the epic's decisions.
- [ ] A phrase and a place return an MP4 file that fits the place, with a poster and its credit, from the cache on the
      second call.
- [ ] With no key, no requests left or an error, the provider returns nothing and the draft goes on.

## Verify

`make lint`, `make test`, the key check script with the user's key (one request).

## Status

Proposed 2026-11-08. Needs `PEXELS_API_KEY` in `.env` (not set on 2026-11-08).
