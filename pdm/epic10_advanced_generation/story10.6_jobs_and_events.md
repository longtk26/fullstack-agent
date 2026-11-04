# Story 10.6 — Background jobs and events

**Epic:** [10 — Advanced generation](epic10_advanced_generation.md) · **Requirements:** FR-34, FR-01 (item 11) · **Depends on:** 10.1

## User story

As a spec author, I want work that runs after a request (on an event, after an operation, or on a schedule) to run
reliably, with retries, and never for a change that was rolled back; email, webhooks and payments build on it.

## Design (decision P5)

- **Queue in Postgres**, no new service: a `jobs` table (kind, payload JSONB, status `queued` / `running` /
  `succeeded` / `failed` / `dead`, attempts, max attempts, `run_at`, lock owner and time, last error) from the
  plugin's Alembic migration. Workers take jobs with `SELECT … FOR UPDATE SKIP LOCKED`, are woken by
  `LISTEN/NOTIFY` with a polling fallback, retry with exponential backoff, recover stale locks, and shut down
  gracefully.
- **Transactional outbox:** `enqueue(...)` and `emit(event, payload)` write into the same session as the use case,
  so a job exists only if the business change committed (use-case event hook). An event fans out to the handlers
  subscribed to it (custom jobs, email 10.7, webhooks 10.8).
- **Schedules:** cron triggers run in the worker loop (`croniter`); one row per (schedule, run time), unique, so two
  workers never run the same tick.

## Acceptance criteria

- [ ] `backgroundJobs[].trigger` is one of `{event: "<entity>.created|updated|deleted|<custom>"}`,
      `{operation: "<operationId>"}` or `{cron: "<expr>"}`; the validator checks event names and operation ids. CRUD use
      cases emit their entity events only when something subscribes.
- [ ] Built-in actions (send email, deliver webhook) are deterministic; a custom job body is written by the engine
      with the jobs API in its context pack; an ambiguous one goes to `unresolved`.
- [ ] `src/libs/jobs/` (enqueue, emit, worker, registry) and `python -m src.worker` (`--once` runs what is due and
      exits); job handlers are idempotent by job id.
- [ ] Template tests: a job enqueued in a rolled-back transaction never runs; retry then dead after max attempts; two
      workers never take the same job; a cron tick runs once.
- [ ] Previews run a `preview-worker-<genId>` container from the same image; the agent UI shows its logs next to the
      backend's. The validation smoke check enqueues a job and runs `--once`.
- [ ] Manifest `jobs` (kinds, triggers, schedules).

## Status

**Planned (2026-11-04).** Replaces the job half of the old story 10.4 (stub only).
