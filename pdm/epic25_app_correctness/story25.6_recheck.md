# Story 25.6 — Re-check: the lab set and a fresh requirement

**Epic:** [25 — App correctness](epic25_app_correctness.md) · **Requirements:** FR-39 · **Depends on:** 25.1–25.5

## User story

As the user, I want proof that the fixes make apps more correct in general, not only for the three apps they were
found in.

## Steps

1. Re-run the three lab requirements (one per workflow shape) with their frozen expectations (`lab/business-value`,
   `--business-from` the 2026-11-07 runs), on the default draft provider (Epic 24) and the Antigravity code engine.
2. Write one **fresh requirement** in a domain and workflow shape not used so far, chosen by the user, and run it end
   to end.
3. Compare with the 2026-11-07 baseline in this story's Status: refused, hidden, paths completed, met of decided.

## Acceptance criteria

- [ ] "Wrong roles refused" and "hidden from others" are ≥ 90% met in each of the four apps.
- [ ] At least the golden path of each app completes end to end through the API.
- [ ] No new failure in the static and app golden tests.

## Verify

Real runs with the user's go (Antigravity on the account login; Gemini API only if the user chooses it).

## Status

**Moved into 26.7 (2026-11-07).** The re-check runs with Epic 26's evaluation (the lab's checker, now in the product)
on the user's limit of two requirements and `agy` only, instead of the lab's Gemini-based scripts. Results in 26.7.
