# Story 8.2 — CLI invocation & validation spans

**Epic:** [8 — Observability](epic8_observability.md) · **Requirements:** FR-13 (CLI duration/status/usage, repairs) · **Depends on:** 8.1, 3.2, 6.2

## User story

As an operator, I want CLI calls and validation checks visible as spans with timing and cost, because LangSmith
does not instrument Claude Code or Antigravity internals automatically.

## Acceptance criteria

- [ ] The engine adapter wraps each invocation in a `@traceable(run_type="tool", name="engine:<name>")` span with
      inputs `{purpose, prompt_id@version, workdir (relative), max_turns}` and outputs
      `{status, exit_code, duration_ms, turns, usage, cost_usd, changed_files}`. `cli_error` sets the span error.
- [ ] `tool_use` events from stream-json become child spans (`tool:<Name> <target>`), sampled to at most 200 per invocation.
- [ ] Each validation check is a span `check:<name>` (status, duration, failure summary). `repair_code#n` spans
      carry `attempt` and diff stats.
- [ ] Token and cost totals are aggregated on the root run metadata and in `report.json`.
