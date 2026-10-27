# Story 8.1 — LangSmith workflow tracing & secret masking

**Epic:** [8 — Observability](epic8_observability.md) · **Requirements:** FR-13, NFR 8.5 · **Depends on:** 4.3

## User story

As an operator, I want each generation to be one correlated LangSmith trace, so that I can debug and evaluate runs.

## Acceptance criteria

- [x] Enabled when `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` are set. Otherwise a no-op, and nothing fails.
- [x] The graph is invoked with `config={run_name: "backend-generation", run_id: <uuid>, tags: [engine, specVersion],
      metadata: {generation_id, owner_id, engine, spec_sha256, prompt_versions, generator_version}}`.
      `trace_id` and the LangSmith run URL are stored on `generations`.
- [x] Every log line and event carries `generation_id` and `trace_id` (NFR 8.5 log/trace correlation).
- [x] The redactor is applied through the LangSmith client `hide_inputs` / `hide_outputs` hooks and reused by events and logs:
      known env secret values, `Authorization`/`Bearer` tokens, `sk-ant-*`, `AIza*`, password fields, and
      DB URLs with credentials.
- [x] Graph state in traces contains refs only (no file contents above 4 KB).
- [x] The final run output includes the final status, validation summary and error summary.
- [x] `LANGSMITH_PROJECT` and trace retention are configurable (NFR 8.5).

**Status (2026-10-27):** done (`src/orchestrator/tracing.py`, `runner._open_trace`). Deviations and notes:
- Spans are built with the LangSmith RunTree API, not LangGraph's callback tracer, which is switched off for the
  graph run (`tracing_context(enabled=False)`). The callback tracer would add internal runnables (routing, channel
  writes) and name nodes without their attempt; ours follow the Epic 8 tree (`run_validation#2`). The graph config
  still carries `run_name`, tags and metadata; the root run carries the metadata listed above plus `mode`.
- One trace per generation even across a worker restart: the root's dotted order is stored in
  `generations.trace_parent`, and a resumed job adds its spans under the same root.
- `LANGSMITH_AGENT_ID` / `LANGSMITH_AGENT_ENVIRONMENT` (LangSmith agent addressing, beta, enabled per workspace)
  send the trace to that agent's environment instead of `LANGSMITH_PROJECT`. The destination is named in code,
  because the SDK refuses to trace when the environment names both. Verified against the real workspace
  (agent `fullstack-agent`, environment `local`): 51 runs per fake generation, URL stored.
- Without tracing a trace id is still created, so logs and events stay correlated. Log lines carry
  `generation_id` / `trace_id` through a context variable (`configs.log_context`); worker events carry `traceId`
  in their payload (events written by the API before the job starts do not).
- Redaction also masks LangSmith keys (`lsv2_…`); span names (tool targets) are redacted before they are built,
  because the client's hooks cover only inputs, outputs and metadata.
- Retention: LangSmith keeps traces per its project setting; locally `TRACE_RETENTION_DAYS` (default 30) prunes
  model calls and sandbox records of old generations.
