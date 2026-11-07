# Story 26.7 — Final check

**Epic:** [26 — Main business workflows](epic26_business_workflows.md) · **Requirements:** FR-40 · **Depends on:** 26.1–26.6, Epic 25

## User story

As the user, I want to see the whole business layer work on real requirements before it becomes the default.

## Steps

1. The three lab requirements and Epic 25's fresh requirement (four workflow shapes), end to end on the provider the user chooses (Epic 24)
   and the Antigravity code engine: discovery, expectations, binding, generation, tour, evaluation, Business tab.
2. The same four with `businessWorkflows` off (D7): the evaluation still runs against the frozen expectations of the
   first run, so both apps are measured the same way; compare met / decided, paths completed, refused, hidden.
3. Each demo role's tour on each app, on mocks and live.

## Acceptance criteria

- [ ] All four apps show the tour per role and a complete Business tab.
- [ ] The comparison with the option off is written in this story's Status; the user decides whether the business
      layer stays on by default.
- [ ] No generation's status changed because of the evaluation.

## Verify

Real runs with the user's go.
