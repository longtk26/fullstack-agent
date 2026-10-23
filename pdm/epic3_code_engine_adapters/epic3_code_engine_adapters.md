# Epic 3 — Code engine adapters (Claude Code + Antigravity)

## Overview

Wrap code-generation CLIs behind one `CodeEngine` port so the LangGraph workflow never knows which
engine runs. Ship **Claude Code CLI** as the default, **Antigravity CLI (`agy`)** as the second engine,
and a **FakeEngine** that lets the workflow and UI be built and tested without LLM cost.

**Requirements:** §3.3, FR-08, NFR 8.1 (CLI permissions), 8.3 (limits), 8.4 (replaceable provider), 8.5

## Port

```python
class ICodeEngine(ABC):
    name: str
    async def run(self, req: EngineRequest, on_event: Callable[[EngineEvent], Awaitable[None]]) -> EngineResult: ...
    async def cancel(self, invocation_id: str) -> None: ...

EngineRequest  = {invocation_id, purpose, workdir, prompt, context_files[], allowed_tools, max_turns, timeout_s, env_allowlist}
EngineResult   = {status: ok|cli_error|timeout|cancelled|limit_exceeded, exit_code, duration_ms, turns,
                  usage: {input_tokens, output_tokens, cost_usd}?, changed_files[], stdout_ref, stderr_ref,
                  final_message, raw_events_ref}
EngineEvent    = {ts, kind: tool_use|tool_result|message|usage|error, summary, data (redacted)}
```

`status=cli_error` (the engine itself failed) is always kept separate from validation failures of the
generated code (NFR 8.5).

**Status (2026-10-23):** done on `feat/epic3-code-engines`. Claude Code verified with real CLI runs; Antigravity
spike = **go** (API key / ADC), adapter built and tested against recorded event shapes, authenticated run still
pending a Gemini key — see [docs/engines/antigravity.md](../../docs/engines/antigravity.md).
Code lives in `agent-api/src/engines/` (port, runner, adapters, prompts) and `agent-api/prompts/`.

## Stories

| # | Story | Depends on |
|---|---|---|
| 3.1 | [CodeEngine port, normalized result & FakeEngine](story3.1_code_engine_port_and_fake.md) | 1.1 |
| 3.2 | [Claude Code CLI adapter](story3.2_claude_code_adapter.md) | 3.1 |
| 3.3 | [Antigravity CLI spike & adapter](story3.3_antigravity_adapter.md) | 3.1 |
| 3.4 | [Versioned prompts & engine context files](story3.4_prompts_and_context_files.md) | 3.1 |

## Epic acceptance

- The same workflow run completes with `engine=fake` and `engine=claude_code`. `engine=antigravity` also
  completes, or the spike outcome is documented with the reason.
- Killing a job mid-CLI-call leaves no orphan CLI process.
