# Story 8.3 — Local trace store & trace API

**Epic:** [8 — Observability](epic8_observability.md) · **Requirements:** FR-13, FR-15 · **Depends on:** 8.2

## User story

As a UI user, I want to see the trace waterfall inside the agent UI, whether or not LangSmith is configured.

## Acceptance criteria

- [x] `GET /api/v1/generations/{id}/trace` → span tree built from `node_runs`, `cli_invocations`, `validation_runs`
      and repair records: `[{spanId, parentId, kind: lane|node|engine|llm|tool|check|sandbox, name, status, startedAt,
      endedAt, durationMs, attrs{tokens,cost,exitCode,attempt,...}, refs{stdout,stderr,patch}}]`.
- [x] `GET /api/v1/generations/{id}/trace/spans/{spanId}/output?stream=stdout|stderr&tail=500` → redacted
      text excerpt from the ref (size-capped).
- [x] The response includes `langsmithUrl` when available, for a deep link.
- [x] Spans for a running job are returned with `endedAt=null`. The UI refreshes on SSE `step.*` / `validation.check` events.

**Status (2026-10-27):** done (`GET /generations/{id}/trace`, `…/trace/spans/{spanId}/output`,
`modules/shared/domain/telemetry/trace.py`). Notes:
- The tree is built from `node_runs`, `cli_invocations`, `model_calls`, `validation_runs` and a new
  `sandbox_execs` table; the response also has the usage rollup (8.4) and the root span (`kind: generation`).
  Backend-only generations have no lane level; every span carries `lane: backend`.
- Output excerpts: engine spans read the CLI logs from the job workspace (available until workspace retention,
  72 h), check spans the stored check output, repair spans the `repair-<n>.patch` artifact (`stream: patch`).
  Everything is redacted, including the span tree itself.
- The preview deployment is not a span: previews start after the job, outside its trace.
