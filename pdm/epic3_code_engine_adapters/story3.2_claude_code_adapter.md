# Story 3.2 — Claude Code CLI adapter

**Epic:** [3 — Code engines](epic3_code_engine_adapters.md) · **Requirements:** FR-08, FR-13 · **Depends on:** 3.1 · **Open question:** Q3

## User story

As the workflow, I want to invoke Claude Code non-interactively inside a job workspace with strict limits,
and receive a normalized result plus a live event stream.

## Acceptance criteria

- [x] Invocation (verified with a real run of Claude Code 2.1.245):
      `claude -p --output-format stream-json --verbose --max-turns <n> --permission-mode acceptEdits
      --tools Read,Write,Edit,Glob,Grep,Skill --allowedTools <same> --disallowedTools Bash,WebFetch,WebSearch,Write(.claude/**),Edit(.claude/**)
      --strict-mcp-config --append-system-prompt <guardrails>`. The prompt is sent on **stdin**, not argv.
      `--tools` is required: `--allowedTools` alone only pre-approves and leaves other tools available.
- [x] Isolation: `cwd=<workspace>`, per-job `HOME` + `CLAUDE_CONFIG_DIR` (no user settings, MCP servers or hooks
      leak in), `ANTHROPIC_API_KEY` (or a copied subscription credentials file) passed only to this process.
- [x] Workspace `.claude/settings*.json`, `.claude/hooks` and `.mcp.json` are deleted before each run and writes to
      `.claude/**` are denied — project hooks run shell commands, so generated content must not plant them.
- [x] Each stream-json line is parsed into an `EngineEvent` (assistant text summary, tool_use name + target
      path, tool_result ok/err). The final `result` event fills `turns`, `usage`, `cost_usd`, `session_id`.
- [x] Non-zero exit, `is_error` result, malformed stream or auth failure → `status=cli_error` with a short
      normalized reason (`auth`, `rate_limit`, `max_turns`, `crash`).
- [x] Bash is not allowed: the engine edits files only, and all code execution happens in the sandbox (Epic 6).
      This is the main control for "CLI permissions restricted to approved operations".
- [x] Integration test (`tests/live/`, opt-in with `BGA_LIVE_ENGINE_TESTS=1`): generate a one-file hello app. Also run
      manually during development; its sanitized stream is the parser fixture.

## Technical notes

- If the turn limit is hit while writing, the partial work stays in the workspace, and validation and repair decide what happens next.
