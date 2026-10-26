# Test doubles and testing-only switches

Everything in this list exists **for tests, demos or local development only**. None of it is used when a real
engine (`claude_code`, `antigravity`) generates a backend. If you add a new fake, stub, fixture-driven mode or
test-only flag, add it here and mark it at its definition.

## Fakes that run inside the product

| What | Where | Used by | Real-generation behaviour it replaces |
|---|---|---|---|
| **Fake engine** (`engine: "fake"`) | `agent-api/src/engines/fake_engine.py` | unit/workflow tests, UI demos, `make up` smoke runs | The LLM CLI. It replays scripted file writes (`FakeStep`s) and never calls a model. Shown in the engine list only when `ENABLE_FAKE_ENGINE=true`. |
| **Golden two-entity project** | `agent-api/src/engines/golden/two_entity/` | the fake engine's script (`demo_scenario`); tests (`tests/generation_helpers.golden_project`) | A hand-written, convention-correct implementation of **`examples/specs/two-entity.json` only**. The fake engine copies it one module per call and plants one syntax error in the tasks router so the repair loop runs. With any other spec a fake run **fails validation** — that is expected. |
| **Static validation runner** | `StaticValidationRunner` in `agent-api/src/orchestrator/validation.py` | `SANDBOX_ENABLED=false` (the default in `tests/conftest.py`) | The sandbox pipeline. It only runs the syntax and conventions checks; every check that would execute code is reported `not_run`, never `passed`. |

`FAKE_ENGINE_DELAY_SECONDS` (default 0.3) slows each fake step so the UI's live view can be watched.

## Test-only fixtures

| What | Where | Purpose |
|---|---|---|
| Fake CLI binaries | `agent-api/tests/fixtures/engines/bin/fake_claude`, `fake_agy` | Stand in for the real `claude` / `agy` executables in adapter tests (argv, stream parsing, timeouts). |
| Recorded Claude stream | `agent-api/tests/fixtures/engines/claude_stream_ok.jsonl` | Sanitized stream-json output for parser tests. |
| Invalid / base specs | `agent-api/tests/fixtures/specs/` | One invalid spec per validator error code. |
| Plan snapshots | `agent-api/tests/fixtures/plans/*.plan.json` | Expected planner output; refresh deliberately with `UPDATE_SNAPSHOTS=1`. |
| Frontend site snapshot | `agent-api/tests/fixtures/frontend/` | Importer regression input. |
| Fake preview runtime | `agent-api/tests/preview_fakes.py` (`FakePreviewRuntime`) | In-memory stand-in for `DockerPreviewRuntime` so the preview lifecycle (start, limits, TTL, reconcile, commands) is tested without Docker. The real containers are covered by `tests/sandbox/test_preview_docker.py`. |

`examples/` (repo root) is **not** test-only: the UI serves it for "Load example" / "Load sample". The golden
project above is written against `examples/specs/two-entity.json`, so change both together.

## Local-development defaults (never production values)

| What | Where | Note |
|---|---|---|
| Seeded users | `SEED_USERS` in `.env.example` (`admin@bga.local`, `user@bga.local`) | Created at API startup for local login. Replace or empty it for any shared deployment. |
| Test databases | `tests/conftest.py` | Uses `<DB>_test`, Redis db 15, a fixed JWT secret, in-memory rate limits, a temporary `ARTIFACT_ROOT` and a 1 s `PREVIEW_COMMAND_TIMEOUT_SECONDS`. |

## Opt-in test suites and flags

| Flag | Effect |
|---|---|
| `BGA_SANDBOX_TESTS=1` | Runs `tests/sandbox/` against the real Docker sandbox (needs Docker and `make runner`), including a real preview container built from `backend.zip` (needs network for its `pip install`). Workspaces go under `.data/test-sandbox/` because Docker Desktop only shares configured paths. |
| `BGA_KEEP_SANDBOX_DIRS=1` | Keeps those sandbox workspaces for inspection. |
| `BGA_LIVE_ENGINE_TESTS=1` | Runs `tests/live/` with the real CLIs (costs money, needs credentials). |
| `UPDATE_SNAPSHOTS=1` | Rewrites the plan snapshots. |

Sandboxes and previews are labelled with the agent instance (a hash of the database name, so the Docker worker and a host dev worker on the same database are one instance), so the test suite and the
Docker stack can share one Docker daemon without cleaning up each other's containers.
