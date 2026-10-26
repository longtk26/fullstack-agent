# Story 3.3 — Antigravity CLI spike & adapter

**Epic:** [3 — Code engines](epic3_code_engine_adapters.md) · **Requirements:** FR-08, NFR 8.4 · **Depends on:** 3.1 · **Open question:** Q4

## User story

As a user, I want to choose Antigravity as the generation engine so that I can compare engines and avoid
depending on a single provider.

## Part A — Spike (time-box: 1 day) — done 2026-10-23, verdict **go**, see [docs/engines/antigravity.md](../../docs/engines/antigravity.md)

Third-party sources and early findings to confirm or reject. Record the results in `docs/engines/antigravity.md`:

- [x] Headless mode: `agy -p "<prompt>"`. Is stdin supported for long prompts?
- [x] Output format: `--output-format json|stream-json`. Capture the event schema and where usage/cost appear, if anywhere.
- [x] Approvals: what is the non-interactive approval policy (`--dangerously-skip-permissions`, `--approve`,
      `--sandbox`)? Can tools be restricted to file edits only (no shell)?
- [x] Auth in a container: API key env var vs Google login token. Which works headless?
- [x] **Known issue:** `agy -p` is reported to hang when stdout is piped or spawned from a subprocess
      ([issue #318](https://github.com/google-antigravity/antigravity-cli/issues/318)). Test on the pinned version.
      If it reproduces, test running under a PTY (`pty.openpty` / `pexpect`).
- [x] Context file convention (`AGENTS.md`? `GEMINI.md`?) and max turns or limit flags.
- [x] **Skills:** does `agy` load workspace skills (e.g. `.agents/skills/<name>/SKILL.md`, the layout this repo
      already uses)? If not, the fastapi-skills content is inlined into the context file (3.4).
- [x] Spike exit: **go** (adapter below) or **no-go** (engine hidden from UI, findings documented).

## Part B — Adapter (if go)

- [x] `AntigravityEngine` implements `ICodeEngine` through `SubprocessRunner` using stream-json **stdin** mode (PTY not needed so far; revisit if an authenticated run hangs),
      with the same workspace, env-scrubbing and timeout rules as 3.2.
- [x] Events and usage mapped into `EngineEvent` / `EngineResult`. Missing usage → `null` (not zero).
- [x] Tool restriction equivalent to "edit files, no shell": per-job `settings.json` denies `command(*)`, URL access and MCP;
      headless mode soft-denies shell anyway. `--max-turns` does not exist, so finished `agent_response` steps are counted and the run is stopped past the limit.
- [x] Worker image pins the `agy` version.
- [x] The same integration test as 3.2 passes with `engine=antigravity` (live adapter test, account login).
- [x] `ANTIGRAVITY_AUTH=account`: uses the host `agy` login (OS keyring over D-Bus), no `GEMINI_API_KEY`; reported
      unavailable inside a container.
- [x] Own limits: `ANTIGRAVITY_MAX_TURNS=150`, `ANTIGRAVITY_TIMEOUT_SECONDS=2400` (agy emits one response per tool call).

**Status (2026-10-26):** account login verified on the host dev worker. First full generation: data layer passed
(310 s), backend step stopped at the shared 40-turn cap → per-engine limits added; a re-run is in progress. Details
in `docs/engines/antigravity.md`.
