# Story 4.2 — Worker process, concurrency & liveness

**Epic:** [4 — Workflow & jobs](epic4_workflow_and_jobs.md) · **Requirements:** NFR 8.2, 8.3 · **Depends on:** 4.1

## User story

As the operator, I want a dedicated worker that runs N jobs in parallel and detects dead jobs, so that the
API stays responsive and crashes never leave jobs stuck as RUNNING forever.

## Acceptance criteria

- [ ] `python -m src.worker` runs an asyncio loop with `WORKER_CONCURRENCY` (default 2) slots using
      `BRPOPLPUSH bga:jobs → bga:processing:<workerId>` (reliable queue).
- [ ] While a job runs, the worker updates `generations.heartbeat_at` every 10 s and keeps a Redis lease key
      `bga:lease:<genId>` (TTL 30 s).
- [ ] Reaper (on worker start and every 60 s): a job in an active status whose lease has expired is re-queued
      for **resume** (4.4). After `MAX_RESUMES` (default 2) it is marked FAILED `WORKER_LOST`.
- [ ] Per-job wall-clock timeout (`JOB_TIMEOUT_SECONDS`, default 1800) → FAILED `TIMEOUT`, and child processes
      and containers are cleaned up.
- [ ] Graceful shutdown on SIGTERM: stop taking new jobs and let running nodes reach a checkpoint (max 60 s),
      then exit. Jobs stay resumable.
- [ ] Structured log line per job transition with `generation_id` and `trace_id`.
