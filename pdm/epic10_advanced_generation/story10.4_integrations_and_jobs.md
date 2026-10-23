# Story 10.4 — Integrations & background jobs (stub + unresolved)

**Epic:** [10 — Advanced generation](epic10_advanced_generation.md) · **Requirements:** FR-01 (items 10, 11), FR-07 (no invention)

## User story

As a spec author, I want specs with external integrations and background jobs to be accepted, with clear stubs and
explicit unresolved items, rather than rejected or silently faked.

## Acceptance criteria

- [ ] `integrations[]` → an output port in `ports/output/` + an adapter stub in `infrastructure/adapters/<name>_adapter.py`
      (the skill's place for third-party integrations) that raises `NotImplementedError`, with env vars
      added to `.env.example` and the manifest `env`.
- [ ] `backgroundJobs[]` → a FastAPI `BackgroundTasks` hook or a documented placeholder, depending on the trigger type.
- [ ] Each one is listed in the manifest `unresolved` with `specPath` and a reason. The generation can still be COMPLETED.
- [ ] Follow-up (out of scope): real HTTP clients and a worker queue in generated backends.
