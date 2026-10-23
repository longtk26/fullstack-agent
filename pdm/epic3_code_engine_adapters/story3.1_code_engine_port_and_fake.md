# Story 3.1 — CodeEngine port, normalized result & FakeEngine

**Epic:** [3 — Code engines](epic3_code_engine_adapters.md) · **Requirements:** FR-08, NFR 8.4

## User story

As a workflow developer, I want one engine interface and a deterministic fake so that LangGraph nodes are
independently testable and engines can be swapped through config.

## Acceptance criteria

- [x] `ICodeEngine`, `EngineRequest`, `EngineResult` and `EngineEvent` as in the epic. `EngineRegistry` resolves
      by name (`claude_code`, `antigravity`, `fake`). Default from env `DEFAULT_ENGINE`, overridable per job
      through `options.engine`.
- [x] Shared `SubprocessRunner` used by all real adapters:
  - argv arrays only, never `shell=True` (FR-08)
  - starts in a new process group, with cancel/timeout → SIGTERM, then SIGKILL after a grace period, for the whole group
  - stdout/stderr streamed line by line to files, with a hard byte cap (default 20 MB). Overflow → `limit_exceeded`
  - minimal env: only allowlisted vars passed through (no DB URLs, no JWT secret)
  - cwd must resolve inside the job workspace (symlink-safe check)
- [x] `changed_files` is computed from a before/after file snapshot (size + mtime, excluding `.git`, `.venv`, caches), so it works with or without the 4.4 git repo.
- [x] `FakeEngine` replays scripted `FakeStep`s per `purpose` (write/copy/delete files, delay, outcome; the last step repeats),
      so Epic 4/6 can script "broken first, fixed on repair". The known-good generated project fixture arrives with Epic 5.
- [x] `GET /api/v1/engines` lists engines with availability; the **worker** publishes engine health to Redis
      (the API image has no CLIs), and the API falls back to a local check marked "worker not reporting".
- [x] Unit tests for timeout, cancel, output cap, and env scrubbing using a dummy script.
