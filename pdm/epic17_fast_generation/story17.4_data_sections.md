# Story 17.4 — Data sections for dynamic apps

**Epic:** [17 — Fast generation](epic17_fast_generation.md) · **Requirements:** FR-30, FR-25 · **Depends on:** 17.2, 13.2

## User story

As a user generating a dynamic web app, I want the frontend lane to finish in minutes, so that the total time is
set by the backend and not by page writing.

## Acceptance criteria

- [ ] Codegen emits an `operationId → hook` map next to the generated `queries.ts`; the library's data sections
      (`CardGrid`, `DataTable`, `DetailView`, `List`, `Form`) take a `DataBinding` and use that map, so one
      component serves every resource (fields, params, route parameters, pagination, sorting).
- [ ] Loading, empty and error states come from `sections[].states`; forms use the generated Zod schemas
      (`src/lib/forms.ts`) and the operation's mutation hook, and `onSuccess` navigates or refreshes as the spec
      says.
- [ ] `project-tracker-dynamic` generates with no engine call on the frontend lane; the mock layer, the
      `MOCK_TEST_API` switch and the live smoke tests (Epic 14) pass unchanged.
- [ ] Status note records the frontend-lane time and which lane now sets the total.

**Status:** open.
