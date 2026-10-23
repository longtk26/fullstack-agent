# Story 4.5 — Progress events & SSE stream

**Epic:** [4 — Workflow & jobs](epic4_workflow_and_jobs.md) · **Requirements:** FR-14, FR-15 · **Depends on:** 4.3

## User story

As a UI user, I want a live stream of what the agent is doing, and if I reconnect I want to see everything I
missed, so that I can follow a long generation.

## Acceptance criteria

- [x] Event types so far: `status.changed`, `job.started`, `job.resumed`, `job.requeued`, `step.started`, `step.finished`,
      `engine.started`, `engine.event`, `engine.finished` (status, usage, changed files), `engine.retry`, `spec.invalid`,
      `validation.check`, `repair.attempt`, `cancel.requested`. `artifact.created` / `preview.status` arrive with Epic 7;
      SSE keep-alive pings replace a `heartbeat` event.
- [x] Every event is `{id, ts, generationId, type, step?, status?, payload}`. It is persisted to `generation_events`
      first, then published on Redis `bga:events:<genId>`.
- [x] `GET /api/v1/generations/{id}/events` (SSE) replays from the `Last-Event-ID` header (or `?after=`), then
      tails live. Heartbeat every 15 s. The stream closes after a terminal status and the final event.
- [x] Payloads pass through the redactor (8.1). Raw stdout is never streamed, only summaries plus refs.
- [x] Per-job event cap (`EVENTS_CAP`, default 5,000). Beyond it only every 20th `engine.event` is stored; other types always are.
