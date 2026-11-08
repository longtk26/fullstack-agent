# Story 28.7 — Final check on real drafts

**Epic:** [28 — A tour you do](epic28_interactive_tour.md) · **Requirements:** FR-42 · **Depends on:** 28.1–28.6

## User story

As the product owner, I want the interactive tour checked on real drafts of different workflow shapes, so that I
know it works beyond the synthetic cases.

## Steps

1. Draft and generate two real requirements (at most two at a time) with business workflows on, through the
   configured draft provider: one with a single role whose workflow creates and then changes a record, one with two
   or more roles that hand a record to each other (an approval or an assignment).
2. Play each role's tour by hand on mocks and on the live API (with the live notice), then read the walker's Tour
   block in the Business tab.
3. Record per workflow: steps completed by doing, steps skipped and why, stuck steps, time to finish; and what a
   first-time user would still not understand.

## Acceptance criteria

- [ ] Every `do` step completes by doing on mocks in both apps, or its skip reason is a known limit noted here.
- [ ] The walker's results match the hand run.
- [ ] Findings and deviations are in this Status, with run folders as evidence.

## Verify

`make lint`, `make test`, `make up`, the two real runs.

## Status

Proposed 2026-11-08.
