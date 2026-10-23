# Story 11.1 — End-to-end MVP acceptance test

**Epic:** [11 — Hardening](epic11_hardening_and_release.md) · **Requirements:** §10, §12.12

## User story

As the team, I want the §10 scenario automated against the real compose stack, so that "MVP done" is a command, not an opinion.

## Acceptance criteria

- [ ] `make e2e` brings up the stack, logs in, and submits `examples/specs/two-entity.json` with `engine=claude_code`
      (or `fake` in CI, with `E2E_ENGINE`). It asserts §10 steps 1–13: 202, status sequence on SSE, every check passed,
      ZIP, OpenAPI and manifest present, operationIds match the spec, LangSmith URL set (if configured), and
      the preview container responds to a CRUD round trip.
- [ ] Step 13: unzip `backend.zip` into a temp dir and follow its README (`docker build` + run with a Postgres) → `/health` 200.
- [ ] Second scenario: import `examples/frontend/revue-de-mode.json` (2.5) → generate → the preview serves the 8 seeded posts,
      with the sort, search and category filter from the page bindings.
- [ ] Agent service unit and integration tests run with `make test`. Coverage is reported for `specs`, `orchestrator` and `engines`.
