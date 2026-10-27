# Story 16.1 — Revisions: model, jobs & workspace restore

**Epic:** [16 — Site revisions & feedback](epic16_site_revisions.md) · **Requirements:** FR-29 · **Depends on:** 13.5, 4.3

## User story

As a user with a finished site, I want to request changes as revisions that build on what I have, without
starting a new generation and without risking the version that works.

## Acceptance criteria

- [ ] Table `generation_revisions`: id `rev_…`, generation_id, number (revision 0 = the original generation), kind
      `spec` | `feedback` | `restore`, target (JSON: page / section / component / asset ids), instructions (text,
      ≤ 4 000 chars), spec_patch (JSON Patch, RFC 6902, against the FrontendSpec), status (QUEUED, RUNNING,
      COMPLETED, COMPLETED_WITH_WARNINGS, FAILED, CANCELLED), base_commit, result_commit, report, created_by,
      timestamps.
- [ ] Allowed only when the generation's frontend lane is COMPLETED (static or dynamic); backend mode → 400
      `REVISIONS_UNSUPPORTED`. One active revision per generation (409 `REVISION_IN_PROGRESS`).
- [ ] API: `POST /api/v1/generations/{id}/revisions`, `GET …/revisions`, `GET …/revisions/{n}`,
      `POST …/revisions/{n}/cancel`; owner checks as for generations; events on the generation's SSE stream
      (`revision.started`, node steps with `revision: n`, `revision.completed` / `revision.failed`).
- [ ] Runs on the existing job queue as its own job kind, graph `revision`: `restore_workspace → apply_revision →
      validate_frontend ⇄ repair_frontend → package_frontend → redeploy_preview`. Repair limit, timeouts, tracing
      and usage work as for generations and are linked to the revision.
- [ ] Workspace restore: the workspace is reused while it exists (`WORKSPACE_RETENTION_HOURS`); afterwards it is
      rebuilt from the artifacts. Packaging stores `frontend.bundle` (a git bundle of the frontend repository) from
      now on; generations packaged before this have none and are restored from `frontend.zip` as a fresh
      repository with one commit (noted in the report).
- [ ] A failed or cancelled revision resets the frontend repository to `base_commit`; the preview keeps serving the
      last good revision.
- [ ] Artifacts: `frontend.zip` is always the latest revision; earlier ones are kept as `frontend-r<N>.zip` (artifact
      retention applies); the manifest gains `revision`.
- [ ] Preview: the image is tagged per revision (`bga-fe-<gen>:r<N>`) — today the build is skipped when the tag
      exists — and the previous revision's image is removed once the new one is serving.
- [ ] Dynamic mode: a revision whose result changes contract-owned files (`src/lib/api/**`, mocks, types) or binds
      to unknown operations fails the `owned-files` / consistency check; the report explains that the change needs
      a backend spec change (the contract is fixed, FR-23).
- [ ] Commit message `revision:<N> <kind>`.
- [ ] Tests: lifecycle with the fake engine; restore from bundle and from ZIP only; failure keeps the previous
      preview; concurrency 409; backend mode 400.
