# Story 31.5 — Final check within the providers' limits

**Epic:** [31 — Sample videos](epic31_sample_videos.md) · **Requirements:** FR-45 · **Depends on:** 31.1–31.4

## User story

As the product owner, I want real drafts with videos from both providers checked for fit, credit, load, accessibility
and limits, so that I know the feature holds up.

## Steps

1. Two real requirements (at most two at a time), with `VIDEO_PROVIDERS=youtube,pexels` and the configured draft
   provider: a static site about something people watch (a `Video` section and a hero that suits motion), and an app
   whose records are videos.
2. Check: each video fits its place (by eye, noted per video); credits show; no YouTube request before play (the
   browser's network log); the background video pauses, and stays still under reduced motion; hero text contrast;
   units and requests spent per draft and per provider; a second draft of the same requirement served from the caches.
3. Use a known unavailable YouTube id and a dead Pexels link in a fixture and check the fallbacks (D6).

## Acceptance criteria

- [ ] Both drafts show fitting, credited videos; YouTube units per draft are recorded and under 1,000; Pexels requests
      per draft are recorded.
- [ ] Findings and deviations are in this Status, with run folders as evidence.

## Verify

`make lint`, `make test`, `make up`, the two real runs.

## Status

Proposed 2026-11-08.
