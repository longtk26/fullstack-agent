# Story 8.2 — CLI invocation & validation spans

**Epic:** [8 — Observability](epic8_observability.md) · **Requirements:** FR-13 (CLI duration/status/usage, repairs) · **Depends on:** 8.1, 3.2, 6.2

## User story

As an operator, I want CLI calls and validation checks visible as spans with timing and cost, because LangSmith
does not instrument Claude Code or Antigravity internals automatically.

## Acceptance criteria

- [x] The engine adapter wraps each invocation in a `@traceable(run_type="tool", name="engine:<name>")` span with
      inputs `{purpose, prompt_id@version, workdir (relative), max_turns}` and outputs
      `{status, exit_code, duration_ms, turns, usage, cost_usd, changed_files}`. `cli_error` sets the span error.
- [x] `tool_use` events from stream-json become child spans (`tool:<Name> <target>`), sampled to at most 200 per invocation.
- [x] Each validation check is a span `check:<name>` (status, duration, failure summary). `repair_code#n` spans
      carry `attempt` and diff stats.
- [x] Token and cost totals are aggregated on the root run metadata and in `report.json`.

**Status (2026-10-27):** done (`JobContext.run_engine`, `validation.traced_check`, `RecordingSandbox`). Notes:
- Spans are built directly with RunTree (see 8.1), not with `@traceable`; the inputs and outputs are as listed.
- Tool spans hang under the model call that issued them (8.4), not directly under the engine span; the sample cap
  of 200 per invocation is counted in `toolsDropped`.
- `repair_code#n` spans carry `attempt`, the changed files and `diffStats` (files / insertions / deletions of the
  repair commit). Every sandbox command is also a `sandbox:<name>` span (`sandbox:alembic upgrade`,
  `sandbox:startup_check`, …), nested under the check that ran it.
- Totals are on the root run's outputs and in `report.json` (`usage`, report version 1.1).
