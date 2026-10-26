# Story 8.3 — Local trace store & trace API

**Epic:** [8 — Observability](epic8_observability.md) · **Requirements:** FR-13, FR-15 · **Depends on:** 8.2

## User story

As a UI user, I want to see the trace waterfall inside the agent UI, whether or not LangSmith is configured.

## Acceptance criteria

- [ ] `GET /api/v1/generations/{id}/trace` → span tree built from `node_runs`, `cli_invocations`, `validation_runs`
      and repair records: `[{spanId, parentId, kind: lane|node|engine|llm|tool|check|sandbox, name, status, startedAt,
      endedAt, durationMs, attrs{tokens,cost,exitCode,attempt,...}, refs{stdout,stderr,patch}}]`.
- [ ] `GET /api/v1/generations/{id}/trace/spans/{spanId}/output?stream=stdout|stderr&tail=500` → redacted
      text excerpt from the ref (size-capped).
- [ ] The response includes `langsmithUrl` when available, for a deep link.
- [ ] Spans for a running job are returned with `endedAt=null`. The UI refreshes on SSE `step.*` / `validation.check` events.
