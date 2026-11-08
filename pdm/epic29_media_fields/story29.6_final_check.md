# Story 29.6 — Final check on real drafts

**Epic:** [29 — Media fields](epic29_media_fields.md) · **Requirements:** FR-43 · **Depends on:** 29.1–29.5

## User story

As the product owner, I want media fields checked end to end on real drafts, so that I know uploads, playback and
subtitles work on the live backend.

## Steps

1. Two real requirements (at most two at a time) through the configured draft provider: one where people watch video
   records with subtitles in two languages, one where people listen to audio records grouped under a parent record.
2. On mocks: every screen plays the samples. On the live preview: upload a real video (≥ 50 MB), an audio file, an
   `.srt` and a `.vtt` file; play them; wait past the signed URL's expiry and keep playing (D8).
3. Record: upload times, playback on Chromium and WebKit (Playwright), subtitle display, what failed.

## Acceptance criteria

- [ ] Both apps upload and play their media on the live backend, with subtitles.
- [ ] Findings and deviations are in this Status, with run folders as evidence.

## Verify

`make lint`, `make test`, `make up`, the two real runs.

## Status

Proposed 2026-11-08.
