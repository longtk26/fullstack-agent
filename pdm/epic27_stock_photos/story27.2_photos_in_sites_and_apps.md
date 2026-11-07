# Story 27.2 — Unsplash photos in sites and apps, with credits

**Epic:** [27 — Stock photos from Unsplash](epic27_stock_photos.md) · **Requirements:** FR-41 · **Depends on:** 27.1

## User story

As someone trying a generated site or app, I want real photos that fit each page and record, credited as Unsplash
requires.

## Steps

1. Sites: `source: "photo"` assets resolve through the provider to their remote URL; the renderer's image shows the
   credit (small, over the photo's corner or below it), linked as the guidelines ask.
2. Apps: image fields in the seed (records' photos) get Unsplash URLs from a phrase per record (the record's label and
   entity, e.g. the product's name); the kit's image cells and detail images show the credit.
3. The project README lists every photo used with its credit.
4. Draft review shows each photo with its credit before generation.

## Acceptance criteria

- [ ] Every Unsplash photo on a generated page carries its credit with both links.
- [ ] App seeds with image fields show photos that match their records.
- [ ] Sites and apps without photos, and the other image providers, are unchanged (static golden snapshots pass).

## Verify

`make lint`, `pnpm exec tsc --noEmit`, `make test`, a site and an app drafted with `IMAGE_PROVIDER=unsplash`.
