# Story 30.4 — Card anatomies and positions

**Epic:** [30 — Design plugins](epic30_design_plugins.md) · **Requirements:** FR-44, FR-37 · **Depends on:** 30.3

## User story

As a user of a generated app, I want records presented in a shape that fits them (a portrait poster, a square
cover, a wide still with the title over it, a picture beside the text) and record pages arranged around what matters,
so that apps of the same kind do not all look alike.

## Context

- Cards today: media on top at 16:9, then title, subtitle, meta, badge (`RoleCards`, `MediaGrid` in `views.tsx`).
- Record pages: `record`, `media` (a 21:9 image on top), `profile` (`AppDetail.tsx`).

## Steps

1. **`card` kind** (new): the anatomy of one record in grid views; props: the record, its field roles, the view's
   size. First plugins:
   - `stacked` (today's: media on top),
   - `overlay` (media fills the card, title and meta over a scrim that keeps AA contrast on the worst pixel),
   - `side` (media left, text right; one column on phones),
   - `text-first` (no media, a large title, meta in a row; for records without images).
2. **Aspect per card:** `aspect` in the entity design: `wide` (16:9), `portrait` (2:3), `square` (1:1), `auto`; code
   picks from the field's name and the archetype when the model gives none (a `poster` → portrait, a `cover` / `album`
   → square).
3. **Record layouts** as `detail-view` plugins: `media-side` (media left, fields right on wide screens), `split-panel`
   (fields left, a side panel with the parent summary and the record's children or related records of the same
   group), `reader` (narrow column for long text fields). Each declares its `needs`.
4. **Grid density** for card views: `columns` (`2`–`6` on wide screens) in the entity design, checked against the card
   anatomy (an `overlay` card at 6 columns keeps its text size).
5. Markers (`data-bga-card`, `data-bga-detail`) for the report's fingerprints.
6. Tests: `complete_design` picks and fallbacks on synthetic specs (no image → `text-first`; a `poster` field →
   portrait); the plugins' checks (30.3) clean.

## Acceptance criteria

- [ ] The four card plugins and three detail plugins are `ready` and pass their gates.
- [ ] The report (30.1) shows more distinct fingerprints than the baseline on the golden set.

## Verify

`make design-plugin-check` for each new plugin, `make app-design-report`, `make test`.

## Status

Proposed 2026-11-08.
