# Story 16.5 — Revision history, diff & restore

**Epic:** [16 — Site revisions & feedback](epic16_site_revisions.md) · **Requirements:** FR-29 · **Depends on:** 16.1, 9.5

## User story

As a user, I want to see what each revision changed and go back to an earlier version when a change was wrong.

## Acceptance criteria

- [ ] Generation page, **Revisions** tab: number, kind, summary (instructions or patch), status, author, time,
      duration, cost; the running revision shows live progress in the existing workflow view (revision graph).
- [ ] `GET /api/v1/generations/{id}/revisions/{n}/diff?against=<m>`: changed files and a unified diff from the
      frontend repository (default `against` = n-1; size-capped, larger files listed without content); the UI shows
      it with the spec patch next to it.
- [ ] `POST …/revisions/{n}/restore` creates a new revision (kind `restore`) whose tree equals revision n — history
      is never rewritten — then validates, packages and redeploys it.
- [ ] Each revision's ZIP can be downloaded while it is retained; the preview header shows which revision it serves.
- [ ] Pending comments (16.4) can be edited or discarded before applying.
- [ ] Tests: diff between revisions; restore creates revision N+1 equal to the target; restore of an expired
      revision ZIP still works from the bundle.
