# Story 8.4 — Model-call spans & cost accounting

**Epic:** [8 — Observability](epic8_observability.md) · **Requirements:** FR-13 · **Depends on:** 8.2

## User story

As an operator, I want to see every model call inside each engine run (which model, how many tokens, how long,
what it cost) and the totals per node, lane and generation, so that I know where time and money go.

## Acceptance criteria

- [ ] The engine stream parsers emit one **model-call record** per model request inside a CLI session. Both CLIs
      report calls in their stream-json output, so no traffic interception is needed (verified 2026-10-26):
  - Claude Code: each `assistant` message carries `message.model` and `message.usage` (input, output,
    cache-creation, cache-read tokens). The CLI repeats a message once per content block, so records are
    **de-duplicated by `message.id`**. There is no per-call latency or cost: latency is measured from the arrival
    time of the message's events (approximate); cost per call is tokens × price, then scaled so the per-model
    sum equals the session's reported `modelUsage[<model>].costUSD` (exact per model and session).
  - Antigravity: each finished `agent_response` step carries `usage` (input, output, thinking, cache-read tokens)
    and `duration_seconds` (reported latency). The stream names no model: it comes from `ANTIGRAVITY_MODEL` or
    the CLI's default. There is no cost in the stream: cost is always *estimated*.
  - Not available from either CLI: the raw HTTP request and exact server-side latency.
  - Stored in a new `model_calls` table (`generation_id`, `cli_invocation_id`, `node_run_id`, `lane`, `seq`,
    `model`, token counts, `duration_ms`, `cost_usd`, `cost_source: reported | estimated`).
- [ ] Cost when the engine reports none (Antigravity): estimated from a configurable price table
      (`MODEL_PRICES` per model: input / output / cache-read per 1M tokens), marked **estimated** everywhere it
      is shown. Unknown model → cost `null`, never a guess.
- [ ] LangSmith: each model call is a child span of its `engine:<name>` span with `run_type="llm"`,
      `metadata.ls_model_name`, and `usage_metadata` (input/output/total tokens) so LangSmith computes and shows
      cost and latency natively; tool calls hang under the model call that issued them.
- [ ] Rollups: per node run, per lane (frontend / backend / integration), per generation — wall time, engine
      time, sandbox time, model calls, tokens by kind, cost (reported + estimated) — exposed in
      `GET /api/v1/generations/{id}/usage` and written to `report.json`.
- [ ] Draft jobs (2.4, 12.4) are traced and accounted the same way, so the cost of drafting is visible too.
