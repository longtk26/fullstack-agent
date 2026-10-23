# Story 8.1 — LangSmith workflow tracing & secret masking

**Epic:** [8 — Observability](epic8_observability.md) · **Requirements:** FR-13, NFR 8.5 · **Depends on:** 4.3

## User story

As an operator, I want each generation to be one correlated LangSmith trace, so that I can debug and evaluate runs.

## Acceptance criteria

- [ ] Enabled when `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` are set. Otherwise a no-op, and nothing fails.
- [ ] The graph is invoked with `config={run_name: "backend-generation", run_id: <uuid>, tags: [engine, specVersion],
      metadata: {generation_id, owner_id, engine, spec_sha256, prompt_versions, generator_version}}`.
      `trace_id` and the LangSmith run URL are stored on `generations`.
- [ ] Every log line and event carries `generation_id` and `trace_id` (NFR 8.5 log/trace correlation).
- [ ] The redactor is applied through the LangSmith client `hide_inputs` / `hide_outputs` hooks and reused by events and logs:
      known env secret values, `Authorization`/`Bearer` tokens, `sk-ant-*`, `AIza*`, password fields, and
      DB URLs with credentials.
- [ ] Graph state in traces contains refs only (no file contents above 4 KB).
- [ ] The final run output includes the final status, validation summary and error summary.
- [ ] `LANGSMITH_PROJECT` and trace retention are configurable (NFR 8.5).
