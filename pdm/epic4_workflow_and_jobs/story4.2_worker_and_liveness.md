# Story 4.2 — Worker process, concurrency & liveness

**Epic:** [4 — Workflow & jobs](epic4_workflow_and_jobs.md) · **Requirements:** NFR 8.2, 8.3 · **Depends on:** 4.1

## User story

As the operator, I want a dedicated worker that runs N jobs in parallel and detects dead jobs, so that the
API stays responsive and crashes never leave jobs stuck as RUNNING forever.

## Acceptance criteria

- [x] `python -m src.worker` runs an asyncio loop with `WORKER_CONCURRENCY` (default 2) slots using
      `BLMOVE bga:jobs → bga:processing:<workerId>` (reliable queue; BRPOPLPUSH is deprecated).
- [x] While a job runs, the worker updates `generations.heartbeat_at` every 10 s and keeps a Redis lease key
      `bga:lease:<genId>` (TTL 30 s).
- [x] Reaper (on worker start and every 60 s): a job in an active status whose lease has expired is re-queued
      for **resume** (4.4). After `MAX_RESUMES` (default 2) it is marked FAILED `WORKER_LOST`.
- [x] Per-job wall-clock timeout (`JOB_TIMEOUT_SECONDS`, default 1800) → FAILED `TIMEOUT`, and child processes
      and containers are cleaned up.
- [x] Graceful shutdown on SIGTERM: stop taking new jobs and let running nodes reach a checkpoint (max 60 s),
      then exit. Jobs stay resumable.
- [x] Structured log line per job transition with `generation_id` and `trace_id`.
- [x] Survives Redis/Postgres restarts (verified on Docker): Redis client with socket/connect timeouts, keepalive,
      idle health checks and retry; Postgres connect timeout + pre-ping (SQLAlchemy) and connection checks
      (checkpointer pool); consume loop and cancel listener back off and reconnect; all services `restart: unless-stopped`.
- [x] Jobs are claimed with an atomic lease (`SET NX`), so a job enqueued twice runs once. The reaper decides by lease
      (not processing-list membership), and a restarted worker clears its own processing list at startup — found when a
      restart reused the same worker id and left a job stuck.
