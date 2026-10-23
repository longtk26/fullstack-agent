# Story 3.1 — CodeEngine port, normalized result & FakeEngine

**Epic:** [3 — Code engines](epic3_code_engine_adapters.md) · **Requirements:** FR-08, NFR 8.4

## User story

As a workflow developer, I want one engine interface and a deterministic fake so that LangGraph nodes are
independently testable and engines can be swapped through config.

## Acceptance criteria

- [ ] `ICodeEngine`, `EngineRequest`, `EngineResult` and `EngineEvent` as in the epic. `EngineRegistry` resolves
      by name (`claude_code`, `antigravity`, `fake`). Default from env `DEFAULT_ENGINE`, overridable per job
      through `options.engine`.
- [ ] Shared `SubprocessRunner` used by all real adapters:
  - argv arrays only, never `shell=True` (FR-08)
  - starts in a new process group, with cancel/timeout → SIGTERM, then SIGKILL after a grace period, for the whole group
  - stdout/stderr streamed line by line to files, with a hard byte cap (default 20 MB). Overflow → `limit_exceeded`
  - minimal env: only allowlisted vars passed through (no DB URLs, no JWT secret)
  - cwd must resolve inside the job workspace (symlink-safe check)
- [ ] `changed_files` is computed from `git status --porcelain` in the workspace (see 4.4).
- [ ] `FakeEngine` replays scripted fixtures per `purpose` (copies a known-good generated project, or
      injects a lint error on the first call to exercise the repair loop) and emits realistic events and usage.
- [ ] Unit tests for timeout, cancel, output cap, and env scrubbing using a dummy script.
