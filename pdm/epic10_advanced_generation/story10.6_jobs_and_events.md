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

- [x] `backgroundJobs[].trigger` is one of `{event: "<entity>.created|updated|deleted|<custom>"}`,
      `{operation: "<operationId>"}` or `{cron: "<expr>"}`; the validator checks event names and operation ids. CRUD use
      cases emit their entity events only when something subscribes.
- [x] Built-in actions (send email, deliver webhook) are deterministic; a custom job body is written by the engine
      with the jobs API in its context pack; an ambiguous one goes to `unresolved`.
- [x] `src/libs/jobs/` (enqueue, emit, worker, registry) and `python -m src.worker` (`--once` runs what is due and
      exits); job handlers are idempotent by job id.
- [x] Template tests: a job enqueued in a rolled-back transaction never runs; retry then dead after max attempts; two
      workers never take the same job; a cron tick runs once.
- [x] Previews run a `preview-worker-<genId>` container from the same image; the agent UI shows its logs next to the
      backend's. The validation smoke check enqueues a job and runs `--once`.
- [x] Manifest `jobs` (kinds, triggers, schedules).

## Status

**Done (2026-11-05)** on `feat/epic10-backend-plugins`.

- **Spec**: `backgroundJobs[].trigger` is `{event}`, `{operation}` or `{cron}` (the string forms `event:…`,
  `operation:…`, `cron:…` are normalized to it); `action` (`log`, built in; `custom`, the engine's) and `maxAttempts`
  (default 5). The validator checks one trigger per job, event names (`<entity>.created|updated|deleted|<name>` of a
  known entity), operation ids and five-field cron expressions; jobs are no longer an "unsupported" warning.
- **The `jobs` plugin** (`orchestrator/plugins/jobs.py`, `templates/plugins/jobs`, `croniter==6.0.0` baked into the
  runner): `src/libs/jobs/` — tables `job_queue` and `job_schedules` (registered for Alembic through the models
  registry, `plan.pluginModels`; the migration check counts them as planned, `plan.pluginTables`), `JobQueue`
  (`enqueue`, `emit`; on the request's session, so it commits or rolls back with the request; dedupe keys), the
  `@job(...)` registry, and a `Worker` (`FOR UPDATE SKIP LOCKED`, a lease for jobs whose worker died, backoff
  30 s × 4ⁿ up to an hour, dead after the last attempt, cron schedules enqueued once per slot). `python -m src.worker`
  runs it; `--once` runs what is due and exits non-zero when a job failed.
- **Events**: a CRUD operation emits its entity's event (`task.created`, …) or its own operation id only when a job
  subscribes (events hook, `jobs: JobQueueDep` from the route); custom code raises `<entity>.<name>` the same way (the
  engine's note says how).
- **Handlers**: `src/jobs/<name>.py`. `log` writes the event to the log; `custom` is a stub the engine fills (an engine
  gap on the module of its trigger); a custom job whose description is under five words is not generated and stays in
  `unresolved`. Handlers get `(payload, ctx)` with the job id, the attempt and a session of their own.
- **Template tests** (`tests/modules/jobs/test_jobs.py`): a job enqueued in a rolled-back transaction never runs; a
  failing job is retried, then dead; two workers in parallel never take the same job; two ticks of one cron slot
  enqueue once; each event job is enqueued by its event.
- **Previews** run `bga-preview-worker-<gen>` from the app's image (the entrypoint's new `worker` command) with the
  app's environment, started after the app is healthy, stopped and removed with it; the agent UI's preview logs show
  its lines (`[worker]`) next to the backend's, in time order. The smoke check runs `python -m src.worker --once`
  after its calls and fails when a job failed. The contract carries `x-bga.jobs` and each operation's `x-bga.emits`;
  the manifest lists `jobs` (names, triggers, actions, attempts).

**Deviations:**

- The queue is PostgreSQL (`SKIP LOCKED`), not Redis: the app needs no other service, and enqueueing joins the
  request's transaction.
- The built-in action is `log` for now; email (10.7) and webhook deliveries (10.8) arrive as their own job kinds.
- A cron job's handler file lives with the other jobs; its engine gap (when custom) is put on the first module.

**Verified:** `make lint`; `tests/test_jobs.py` (6) and the validator tests; `make test` (all pass after the schema
digest update); `BGA_SANDBOX_TESTS=1` for a jobs generation through the workflow
(`test_a_backend_with_background_jobs_passes_its_tests_and_scenarios`): every check passes on the first try, 37
template tests (the four worker tests among them), 19 scenarios and the worker's `--once` run. `make up`, then a
fake-engine backend generation with event and cron jobs (`gen_01M6N6B9CKXSY7JMC5CBXEM83F`): its preview runs the
worker container; creating a task and deleting a project leave `logNewTask` and `logRemovedProject` done after one
attempt, and their log lines appear as `[worker]` in the preview logs.
