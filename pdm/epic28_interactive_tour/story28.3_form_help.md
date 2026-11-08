# Story 28.3 — Form help: field by field, and an example to fill in

**Epic:** [28 — A tour you do](epic28_interactive_tour.md) · **Requirements:** FR-42, FR-35 · **Depends on:** 28.2

## User story

As a new user facing a form in the tour, I want to be shown which fields matter and what a good value looks like,
and to be able to fill the form with an example in one click, so that I can finish the step without guessing.

## Context

- App forms use react-hook-form (`AppForm.tsx`, `useForm`), fields from `components/app/form/` (inputs, dates,
  choices, reference pickers, uploads); each field has its label, help, currency or unit (22.5).
- The contract's operations carry `x-bga.scenarios`; the first success scenario's body is a valid request (the mocks'
  `scenarios` check and the backend smoke check send it).
- Pickers list existing records (`ReferenceField`); `currentUser` and `server` sources are not shown (22.6).

## Steps

1. **Example per form (code).** `frontend/app/files.py` writes `example` on each form in `app.json`: the operation's
   first success scenario body, reduced to the form's visible fields; references and files are left out (they are
   picked on the screen); a value the form's Zod schema would refuse is dropped. Forms without a success scenario get
   no example.
2. **Form registry.** `AppForm` registers its form methods under the form id (`registerForm(id, methods)` in
   `components/app/form/registry.ts`, unregistered on unmount) so the tour can call `setValue` and `trigger`; nothing
   else reads it.
3. **Field by field.** When a `do` step's form is open, the step walks its required fields in order: the spotlight on
   the field, its label and help as the text, "Next field" or completion on the field's `field` signal; optional
   fields are mentioned once ("The other fields are optional").
4. **Fill with an example.** A button on the form step fills the empty fields from `example` (`setValue` with
   `shouldValidate`), picks the first option in each required picker, and leaves uploads to the user (a required
   upload stays highlighted with "Choose a file"). It never overwrites what the user typed and **never submits**
   (D3); the spotlight moves to the submit button.
5. **Live data notice.** When the app runs on the live API, the first form step says once "This creates a real
   record" (the kit knows the mode from the mock switch).
6. Tests: `example` on synthetic contracts (a create with an enum, a date, a decimal with a currency, a reference, a
   file, a server-set owner); vitest: fill leaves typed values, fills the rest, picks a reference, does not submit;
   the field walk skips hidden fields.

## Acceptance criteria

- [ ] Every form step on the golden workflow apps can be completed with "Fill with an example" plus the submit button,
      on mocks, for every role.
- [ ] The tour never submits a form or performs an action by itself.
- [ ] Forms outside the tour are unchanged.

## Verify

`make test`, the kit's vitest and `tsc`, `make up` with a workflow app on mocks.

## Status

Proposed 2026-11-08.
