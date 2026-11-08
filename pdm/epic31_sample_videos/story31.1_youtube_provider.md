# Story 31.1 — The YouTube video provider

**Epic:** [31 — Sample videos](epic31_sample_videos.md) · **Requirements:** FR-45 · **Depends on:** 27.1

## User story

As the drafting code, I want to turn a short phrase into an embeddable, safe, credited YouTube video within the daily
quota, so that sites and apps can show real videos without the model naming any.

## Context

- Epic 27's shape: `images/port.py`, `images/unsplash.py` (search, cache under `ARTIFACT_ROOT/asset-cache/stock/`,
  limits), `images/factory.get_stock_photos()`, `IMAGE_PROVIDER`.
- YouTube Data API v3: `search.list` (100 units), `videos.list` (1 unit), default quota 10,000 units a day per project.

## Steps

1. **Terms first (D7):** read the YouTube API Services Terms of Service and Developer Policies; record here what they
   require for storing ids and metadata, refreshing them, embedding, branding and links, and adjust D3, D5 and D6 to
   them before writing code.
2. **Port** `videos/port.py`: `search(phrase, *, language, duration, count) -> list[VideoHit]` (`id`, `title`,
   `channel`, `channelUrl`, `thumbnail`, `duration`), `available(ids) -> dict[id, bool]`.
3. **Adapter** `videos/youtube.py` (httpx): the filters of D2; `videos.list` for duration and `status.embeddable`;
   the key from settings only; errors and quota exhaustion (`403 quotaExceeded`) end the search with no result, never
   the draft.
4. **Cache and quota:** results cached by phrase + language + duration under `ARTIFACT_ROOT/asset-cache/video/`; a
   local daily counter of units spent (reset at midnight Pacific time, as the quota is) that refuses a search when the
   remaining units are under a margin.
5. **Settings:** `VIDEO_PROVIDERS` (a list of `youtube`, `pexels`; empty by default), `YOUTUBE_API_KEY`; listed in
   `.env.example`; the settings page shows which providers are on. A quick key check script like Epic 27's
   (`videos.list`, 1 unit).
6. **Tests:** the adapter against a recorded responder injected from `tests/` (no network, per the test-code rule);
   cache hits; quota refusal; an unembeddable result filtered out. The responder is listed in
   `docs/development/test-doubles.md`.

## Acceptance criteria

- [ ] The terms' requirements are recorded in this Status and reflected in the epic's decisions.
- [ ] A phrase returns embeddable, safe-search videos with their credit, from the cache on the second call.
- [ ] With no key, no quota or an error, the provider returns nothing and the draft goes on.

## Verify

`make lint`, `make test`, the key check script with the user's key (a few units).

## Status

Proposed 2026-11-08. Key checked the same day (see the epic's Status): `videos.list` and one `search.list` with
D2's filters both answered; 101 units spent.
