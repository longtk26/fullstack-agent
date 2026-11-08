# Story 28.2 — "Do" steps: the user performs the step, the tour waits

**Epic:** [28 — A tour you do](epic28_interactive_tour.md) · **Requirements:** FR-42 · **Depends on:** 28.1

## User story

As a new user, I want the tour to show me the control and let me use it, and to move on only once I have actually
done the step, so that I learn the workflow by doing it.

## Context

- react-joyride 3.2.0: controlled mode (`stepIndex`, `run`), `buttons`, `blockTargetInteraction`,
  `overlayClickAction`, `onEvent(data, controls)`; the tour already runs controlled with `continuous`.
- A form's submit is reached through its "New" button or an action that opens a dialog: the step's target is the
  first control on that path that is on the screen.

## Steps

1. **Controlled index.** `AppTour` keeps `stepIndex` itself; joyride's Next is shown only on `look` and `note` steps.
2. **A `do` step** lets the user click the target (`blockTargetInteraction: false`, the overlay still blocks the rest),
   shows the step's text with "Your turn" and a "Skip this step" link, and listens to `onSignal`: the step's
   `operation` signal completes it (the next step shows after the page settles); a `dialog` signal on the way moves
   the spotlight into the dialog (its form or its submit button) without completing the step.
3. **Path to the control:** when the step's target is a form submit and the form is not on the screen, the step
   points at the control that opens it (the section's "New" or the record action with the same operation); when
   that opens, the spotlight follows.
4. **Errors:** a failed submit keeps the step and points at the first field with an error (the form already shows
   it); the step text adds "Fix the highlighted field and try again".
5. **Timeouts:** a target not found after `beforeTimeout` makes the step a centred note with the reason (D7); the
   tour never blocks the app.
6. Tests (vitest, mocks): a `do` step completes on its operation's signal and not on another operation's; skip moves
   on and records the skip; a dialog form moves the spotlight into the dialog; a 422 keeps the step.

## Acceptance criteria

- [ ] On a workflow app on mocks, each role's `do` steps complete only after the user performs the operation.
- [ ] The user can always skip a step or close the tour; the rest of the app stays usable.
- [ ] `look` and `note` steps behave as in 26.4.

## Verify

`pnpm exec tsc --noEmit`, the kit's vitest, `make design-check-app`, `make up` with a workflow app on mocks: play one
role's tour by hand.

## Status

Proposed 2026-11-08.
