# Story 3.2 — Claude Code CLI adapter

**Epic:** [3 — Code engines](epic3_code_engine_adapters.md) · **Requirements:** FR-08, FR-13 · **Depends on:** 3.1 · **Open question:** Q3

## User story

As the workflow, I want to invoke Claude Code non-interactively inside a job workspace with strict limits,
and receive a normalized result plus a live event stream.

## Acceptance criteria

- [ ] Invocation (flags verified against the pinned `claude --version` in the worker image):
      `claude -p --output-format stream-json --verbose --max-turns <n> --permission-mode acceptEdits
      --allowedTools Read,Write,Edit,MultiEdit,Glob,Grep --disallowedTools Bash,WebFetch,WebSearch
      --append-system-prompt <conventions>`. The prompt is sent on **stdin**, not argv.
- [ ] Isolation: `cwd=<workspace>`, per-job `CLAUDE_CONFIG_DIR` (no user settings, MCP servers or hooks
      leak in), `ANTHROPIC_API_KEY` passed only to this process.
- [ ] Each stream-json line is parsed into an `EngineEvent` (assistant text summary, tool_use name + target
      path, tool_result ok/err). The final `result` event fills `turns`, `usage`, `cost_usd`, `session_id`.
- [ ] Non-zero exit, `is_error` result, malformed stream or auth failure → `status=cli_error` with a short
      normalized reason (`auth`, `rate_limit`, `max_turns`, `crash`).
- [ ] Bash is not allowed: the engine edits files only, and all code execution happens in the sandbox (Epic 6).
      This is the main control for "CLI permissions restricted to approved operations".
- [ ] Integration test (marked, skipped without a key): generate a one-file hello app in a temp workspace.

## Technical notes

- If the turn limit is hit while writing, the partial work stays in the workspace, and validation and repair decide what happens next.
