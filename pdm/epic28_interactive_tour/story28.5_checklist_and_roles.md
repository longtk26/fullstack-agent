# Story 28.5 — A checklist with progress, and following the workflow across roles

**Epic:** [28 — A tour you do](epic28_interactive_tour.md) · **Requirements:** FR-42 · **Depends on:** 28.2, 28.4

## User story

As a user, I want a checklist of my workflow steps that remembers where I stopped, and in a demo I want to follow a
workflow through the other roles' steps, so that I can learn at my own pace and see the whole workflow.

## Context

- Progress today is one `done` flag per user, role and tour version (`localStorage`); the replay is a floating
  "Guide" button (26.4's deviation).
- The auth plugin shows demo accounts on the sign-in page (`data-bga-demo-accounts`, `demo-<role>@example.com`).

## Steps

1. **Progress per step** in `localStorage` (`bga-tour:<version>:<user>`): done, skipped, current; a new tour version
   keeps the steps whose id and operation did not change.
2. **Checklist panel** (a shadcn `Sheet` opened from the "Guide" button, which shows "2 / 5"): per tour, its steps with
   their state, the role of each step, "Continue" from the current step, "Start again". On phones the sheet is a
   bottom drawer. It follows the recipe's look (no new colours).
3. **Start:** on first sign-in the tour starts on the first step not done; the checklist opens when the user closes a
   tour halfway.
4. **Continue as <role>** (only when the app shows demo accounts): a `note` step of another role offers to sign in as
   that role's demo user through the auth plugin's session, and the tour continues there at the same step; the
   checklist shows which role is next. Without demo accounts the note stays as in 26.4.
5. **Done:** the last step shows the workflow's outcome (26.4) and marks the tour done in the checklist.
6. Tests (vitest): progress survives a reload; a version change keeps unchanged steps; "Continue as" signs in as the
   demo user of that role on mocks and resumes the step.

## Acceptance criteria

- [ ] Closing the tour halfway and signing in again continues at the same step.
- [ ] The checklist shows each step's state and role, at 375 and 1440 px, light and dark.
- [ ] In a demo, one person can play a workflow from its first step to its outcome across roles.

## Verify

The kit's vitest and `tsc`, `make design-check-app`, `make up` with a workflow app on mocks: play a two-role workflow
end to end.

## Status

Proposed 2026-11-08.
