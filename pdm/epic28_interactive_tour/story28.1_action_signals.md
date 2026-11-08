# Story 28.1 — Action signals in the kit, step kinds in the tour data

**Epic:** [28 — A tour you do](epic28_interactive_tour.md) · **Requirements:** FR-42, FR-40 · **Depends on:** 26.4

## User story

As the tour, I want to know when the user has done what a step asks (an operation succeeded, a page or dialog
opened, a field was filled), so that a step can complete on the user's action instead of a Next button.

## Context

- Steps in `app.json` `workflows` already carry `operationId`, `page`, `route` and `target` (`tour_workflows`,
  `business/binding.py`); the kit's mutations run through React Query in `AppForm.tsx` (`mutation.mutate`, `onSuccess`)
  and `AppActions.tsx` / `RecordActions.tsx`.
- Targets are the existing `data-bga-section`, `data-bga-action` markers (26.4).

## Steps

1. **One signal.** `components/app/signals.ts`: `signal(kind, detail)` dispatches a `bga:done` `CustomEvent` on
   `window` with `{kind: "operation" | "page" | "dialog" | "field", operationId?, page?, section?, field?, record?}`,
   and `onSignal(handler)` returns an unsubscribe. No dependency, no effect when nobody listens.
2. **Where the kit sends it:** after a mutation's success in `AppForm`, `AppActions`, `RecordActions`, the payment
   action and the upload field (the operation id and the record id from the response); when a page renders its
   sections (`AppPage`); when a dialog or sheet opens with a form; when a form field changes from empty to a valid
   value (`field`, debounced). The signal never carries field values.
3. **Step kinds** in `tour_workflows`: `kind: "do"` when the step's operation is a write and it has a target with an
   action, `"look"` when the target is a section showing data, `"note"` for automatic steps, another role's steps and
   steps with `skip`. `TTourStep.kind` in `app.ts`. The tour version changes, so tours already seen start again once.
4. Tests: `tour_workflows` kinds on synthetic bindings (a write with a form, a write with an action button, a read, an
   automatic step, a step of a role with no screen); a vitest that a successful form submit and a record action each
   send one `operation` signal with the right id, and a failed one (422, 409) sends none.

## Acceptance criteria

- [ ] Every successful write through the kit sends exactly one `operation` signal with its operation id; failures
      send none.
- [ ] Every tour step has a `kind`; a write step without a target is a `note` with its reason.
- [ ] No visual change (`make design-check-app`), and apps without workflows behave as before.

## Verify

`make lint`, `pnpm exec tsc --noEmit` (kit), `make test`, `make design-check-app` on a workflow app on mocks.

## Status

Proposed 2026-11-08.
