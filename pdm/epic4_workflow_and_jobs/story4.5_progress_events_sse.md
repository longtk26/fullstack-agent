# Story 4.5 — Progress events & SSE stream

**Epic:** [4 — Workflow & jobs](epic4_workflow_and_jobs.md) · **Requirements:** FR-14, FR-15 · **Depends on:** 4.3

## User story

As a UI user, I want a live stream of what the agent is doing, and if I reconnect I want to see everything I
missed, so that I can follow a long generation.

## Acceptance criteria

- [ ] Event types: `status.changed`, `step.started`, `step.finished`, `engine.event` (tool use and message summaries
      from 3.x, throttled), `engine.usage`, `validation.check`, `repair.attempt`, `artifact.created`,
      `preview.status`, `log` (non-sensitive), `heartbeat`.
- [ ] Every event is `{id, ts, generationId, type, step?, status?, payload}`. It is persisted to `generation_events`
      first, then published on Redis `bga:events:<genId>`.
- [ ] `GET /api/v1/generations/{id}/events` (SSE) replays from the `Last-Event-ID` header (or `?after=`), then
      tails live. Heartbeat every 15 s. The stream closes after a terminal status and the final event.
- [ ] Payloads pass through the redactor (8.1). Raw stdout is never streamed, only summaries plus refs.
- [ ] Per-job event cap (default 5,000). `engine.event` is sampled beyond the cap.
