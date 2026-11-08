# Story 30.7 — Choosing among more plugins

**Epic:** [30 — Design plugins](epic30_design_plugins.md) · **Requirements:** FR-44, FR-37 · **Depends on:** 30.4–30.6

## User story

As a user drafting two apps of the same kind, I want them to come out different when nothing in my requirement says
otherwise, the same when I draft the same requirement again, and easy to switch in the review, so that variety is real
and under my control.

## Context

- `complete_design` (`frontend/app/design.py`) completes the model's brief with archetype defaults; the requirement's
  look comes first (23.13); the three looks span families (23.7).

## Steps

1. **Candidates:** for each axis, the ready plugins whose `archetypes` include the app's and whose `needs` the
   contract meets; the model's choice wins when it is a candidate, else the archetype default, else the seed's pick
   among candidates.
2. **Seed (D9):** the draft's seed picks among equal candidates for every axis the model left open; the same draft
   gives the same design; "try another layout" in the review is a new seed for layout axes only.
3. **Coherence rules (code):** a recipe's `prefers` breaks ties for card and density; a featured home needs a media
   card; a `terminal` recipe prefers `table` and `compact`. Rules live in descriptors, not in code branches.
4. **Review:** the Design panel lists, per axis, the candidates with their preview screenshots (30.3's `preview.png`);
   switching is a spec edit that re-renders with no engine call.
5. **Prompt:** the choice lists show only candidates for the archetype the requirement suggests, so the prompt does
   not grow with the registry.
6. Tests: candidates per archetype on synthetic specs; the same seed gives the same design; a new seed changes only
   open axes; the requirement's look always wins.

## Acceptance criteria

- [ ] Five drafts of one requirement with different seeds give at least three distinct fingerprints (30.1).
- [ ] The same draft re-applied gives the same design.
- [ ] The prompt's size stays within 10% of today's whatever the registry's size.

## Verify

`make test`, `make app-design-report`.

## Status

Proposed 2026-11-08.
