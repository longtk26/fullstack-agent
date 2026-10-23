# Antigravity CLI (`agy`) — spike results and adapter notes

Spike for Story 3.3, run 2026-10-23 against **agy 1.4.6** (installed in a throwaway `python:3.12-slim` container).
Adapter: `agent-api/src/engines/antigravity/`.

**Verdict: go**, with API-key or ADC auth. An authenticated generation run has **not** been verified yet (no
Gemini key available during the spike); everything else below was checked against the real binary or the
official docs.

## Findings

| Question | Finding | Source |
|---|---|---|
| Install | Go binary from `curl -fsSL https://antigravity.google/cli/install.sh \| bash` (→ `~/.local/bin/agy`). The script always installs *latest* from a manifest (`…/manifests/linux_amd64.json`: `version`, `url`, `sha512`), so the worker image pins the tarball URL + sha512 directly. The documented `--skip-aliases` flag is rejected by the current script. | verified |
| Headless mode | `agy -p "<prompt>"`, or **stream-json stdin mode**: `--input-format stream-json --output-format stream-json`, one `{"event":"user","message":{"content":"…"}}` line per turn; the process ends when stdin closes. The adapter uses stdin mode (no argv length limit; it is the documented subprocess integration). | docs + verified |
| Output events | NDJSON with `event`: `init` (`conversation_id`, `tools`, `permission_mode`), `step_update` (`step_index`, `state` ACTIVE/DONE, `step_type` `agent_response`/`tool`/…, `text_delta`, `tool_info{name, parameters, output, error}`), `result` (`status` SUCCESS/ERROR/CANCELED/…, `response`, `error`, `num_turns`, `usage{input_tokens, output_tokens, thinking_tokens, cache_read_tokens, total_tokens}`). **No cost field.** | docs; `result` verified |
| Exit codes | 0 success (also when a tool was soft-denied); 1 failed run (e.g. auth). Unauthenticated run printed `{"event":"result","result":{…"status":"ERROR","error":"authentication failed or timed out"…}}` and `Error: authentication required…` on stderr, exit 1. | verified |
| Approvals / tools | `--mode accept-edits`; headless soft-denies shell commands by default. Permission rules live in `~/.gemini/antigravity-cli/settings.json` → `permissions.allow/deny/ask` with `action(target)` (`read_file`, `write_file`, `command`, `read_url`, `execute_url`, `mcp`). The adapter writes a per-job settings file that denies `command(*)`, URL access and MCP. `--sandbox` / `enableTerminalSandbox` restricts the terminal. | docs |
| Auth in a container | Account login needs an OS keyring (not available in Docker) → **not usable**. Supported for us: `GEMINI_API_KEY` **plus** `"modelProvider": "gemini"` in settings.json (the key alone is ignored), or ADC (`AGY_ADC_AUTH=true` + `GOOGLE_APPLICATION_CREDENTIALS`). | docs |
| Subprocess hang ([issue #318](https://github.com/google-antigravity/antigravity-cli/issues/318)) | Reported for `agy -p` with piped stdout. Stdin stream-json mode returned promptly over pipes in the probe (auth-error path). **PTY fallback not implemented**; revisit if an authenticated run hangs. | partially verified |
| Context files | `AGENTS.md`, `GEMINI.md`, `.agents/AGENTS.md`, `.agents/rules/*.md` (needs frontmatter). Max 24 KB per file. | docs |
| Skills | Workspace skills at `.agents/skills/<name>/SKILL.md`. | docs |
| Max turns | **No flag.** The adapter counts finished `agent_response` steps and stops the process past `max_turns` (`limit_exceeded`/`max_turns`). `--print-timeout` bounds wall-clock time. | docs |
| Self-update | The binary keeps updater state under `$HOME` (`updater/`, `last_check.timestamp`). Each job gets its own `HOME`; whether agy self-updates the pinned binary in place is unverified. | observed |

## Adapter decisions

- Per-job `HOME` (`<state>/engine-home/antigravity/`) holding the generated `settings.json`; nothing from the worker's own home is used.
- `prepare_workspace`: skills → `.agents/skills/`, conventions → managed section in `AGENTS.md` (points at the template's `CLAUDE.md` when present).
- Before every run `.agents/hooks.json` and `.agents/rules/` are removed from the workspace, so generated content cannot plant hooks or rules.
- Usage: `input_tokens + cache_read_tokens` → input, `output_tokens + thinking_tokens` → output, cost `null`.

## Policy note

A forum reply (not confirmed as Google staff) says orchestrating `agy` headless via process pipes is supported and
consumes the same entitlements as interactive use, while extracting OAuth tokens is not. Related threads about
consumer plans were still open in October 2026. Our container setup uses API keys or ADC, not account logins.
[forum thread](https://discuss.ai.google.dev/t/is-external-orchestration-of-antigravity-cli-headless-mode-supported-with-account-based-usage/183051)

## To do before relying on it

1. Run `make` stack with `GEMINI_API_KEY` set and `DEFAULT_ENGINE=antigravity`; generate a hello app (same as the Claude integration test).
2. Confirm the permission rules block `command(*)` without prompting, and that skills under `.agents/skills/` are picked up headless.
3. Confirm no self-update happens inside the worker image.
