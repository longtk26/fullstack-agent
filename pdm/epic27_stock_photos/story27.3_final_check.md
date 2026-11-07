# Story 27.3 — Final check

**Epic:** [27 — Stock photos from Unsplash](epic27_stock_photos.md) · **Requirements:** FR-41 · **Depends on:** 27.1, 27.2

## User story

As the user, I want to see real requirements generated with Unsplash photos before it becomes the default.

## Steps

1. One static site and one dynamic app with photos, end to end, one at a time (the machine's limit), within the
   demo application's 50 requests per hour.
2. Check every photo fits its place, is credited, and that the download tracking calls were made.

## Acceptance criteria

- [ ] Both generations show matching, credited photos; requests used are written in this story's Status.
- [ ] The user decides whether `unsplash` becomes the default `IMAGE_PROVIDER`.

## Verify

Real runs with the user's go.
