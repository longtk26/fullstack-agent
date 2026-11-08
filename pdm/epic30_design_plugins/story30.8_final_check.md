# Story 30.8 — Final check

**Epic:** [30 — Design plugins](epic30_design_plugins.md) · **Requirements:** FR-44 · **Depends on:** 30.1–30.7

## User story

As the product owner, I want the report and real drafts to show that apps of the same kind now look different, and
that the plugins hold up in real apps, so that I can decide how many plugins to add next and where.

## Steps

1. `make app-design-report` against 30.1's baseline: distinct fingerprints, signed-in similarity, unused plugins.
2. Two real drafts (at most two at a time), of the same archetype with different products, through the configured
   draft provider; screenshots of every area signed in, in the looks they were given.
3. Record the gaps the report and the screenshots show, as the first entries of the plugin backlog (the list the guide
   points at for "what to add next").

## Acceptance criteria

- [ ] The report beats the baseline on distinct fingerprints and signed-in similarity, or this Status explains why.
- [ ] The two drafts differ in at least four axes and pass the design check.
- [ ] The plugin backlog has its first entries.

## Verify

`make lint`, `make test`, `make app-design-report`, `make up`, the two real runs.

## Status

Proposed 2026-11-08.
