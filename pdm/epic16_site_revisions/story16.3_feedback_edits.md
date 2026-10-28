# Story 16.3 — Feedback on a section, component or page

**Epic:** [16 — Site revisions & feedback](epic16_site_revisions.md) · **Requirements:** FR-29 · **Depends on:** 16.1, 13.3

## User story

As a user, I want to point at part of my site, describe what should change, and get exactly that part updated.

## Acceptance criteria

- [ ] `kind: "feedback"` with up to 10 items, each `{ target, instructions }`; target is `{ page }`,
      `{ page, section }` or `{ component }` and must exist in the plan. Several comments go into one revision to
      save engine calls.
- [ ] Feedback on a **catalogue section** (17.2) is turned into a JSON Patch of the FrontendSpec by one structured
      model call (prompt `revise_spec/v1`, output checked against the 16.2 allow-list and validated like a spec
      edit); the revision then runs as a spec edit, with no engine (CLI) session. Only feedback on a custom
      component (17.3), or that the catalogue cannot express, goes to the engine as below; the revised component
      gets a new cache key.
- [ ] Scope from the frontend plan: editable files = the route file, the component file and its hook, the section
      component; new files allowed only under the component's feature folder. Read-only context: the plan entry,
      theme, the spec section and, in dynamic mode, the contract operations the page uses.
- [ ] Prompt `revise_frontend/v1` with `nextjs-skills` installed, as in 13.3. The project rules
      (`frontend_conventions.md`) still apply: "make it red" becomes a theme token or is reported, never a
      hard-coded colour.
- [ ] Changes outside the scope are reverted and reported (event `revision.out_of_scope`); the revision continues
      with the in-scope changes.
- [ ] Targeting a shared component: the UI warns "used by N pages" before submit; every page using it is built and
      its smoke test runs.
- [ ] Validation and repair as in 13.4; the engine call is in usage and traces under node `revise_frontend`.
- [ ] Fake engine: feedback goldens (e.g. the `static-landing` hero with a shorter heading and a second button),
      listed in `docs/development/test-doubles.md`.
- [ ] Out of scope: adding or removing pages, new data bindings, backend changes.
- [ ] Tests: scope computation per target type; out-of-scope edits reverted; owned-file edits rejected.
