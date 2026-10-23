# Story 3.3 — Antigravity CLI spike & adapter

**Epic:** [3 — Code engines](epic3_code_engine_adapters.md) · **Requirements:** FR-08, NFR 8.4 · **Depends on:** 3.1 · **Open question:** Q4

## User story

As a user, I want to choose Antigravity as the generation engine so that I can compare engines and avoid
depending on a single provider.

## Part A — Spike (time-box: 1 day)

Third-party sources and early findings to confirm or reject. Record the results in `docs/engines/antigravity.md`:

- [ ] Headless mode: `agy -p "<prompt>"`. Is stdin supported for long prompts?
- [ ] Output format: `--output-format json|stream-json`. Capture the event schema and where usage/cost appear, if anywhere.
- [ ] Approvals: what is the non-interactive approval policy (`--dangerously-skip-permissions`, `--approve`,
      `--sandbox`)? Can tools be restricted to file edits only (no shell)?
- [ ] Auth in a container: API key env var vs Google login token. Which works headless?
- [ ] **Known issue:** `agy -p` is reported to hang when stdout is piped or spawned from a subprocess
      ([issue #318](https://github.com/google-antigravity/antigravity-cli/issues/318)). Test on the pinned version.
      If it reproduces, test running under a PTY (`pty.openpty` / `pexpect`).
- [ ] Context file convention (`AGENTS.md`? `GEMINI.md`?) and max turns or limit flags.
- [ ] **Skills:** does `agy` load workspace skills (e.g. `.agents/skills/<name>/SKILL.md`, the layout this repo
      already uses)? If not, the fastapi-skills content is inlined into the context file (3.4).
- [ ] Spike exit: **go** (adapter below) or **no-go** (engine hidden from UI, findings documented).

## Part B — Adapter (if go)

- [ ] `AntigravityEngine` implements `ICodeEngine` through `SubprocessRunner` (PTY mode when required),
      with the same workspace, env-scrubbing and timeout rules as 3.2.
- [ ] Events and usage mapped into `EngineEvent` / `EngineResult`. Missing usage → `null` (not zero).
- [ ] Tool restriction equivalent to "edit files, no shell". If that cannot be enforced, run the CLI
      **inside the sandbox container** (Epic 6.1) with no network except the model endpoint, and document this.
- [ ] Worker image pins the `agy` version.
- [ ] The same integration test as 3.2 passes with `engine=antigravity`.
