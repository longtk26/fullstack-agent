# Story 6.2 — Validation check pipeline (`run_validation`)

**Epic:** [6 — Validation & repair](epic6_validation_and_repair.md) · **Requirements:** FR-11 · **Depends on:** 6.1, 5.5

## User story

As a user, I want each validation check to report passed only if its command really exited 0, so that a
COMPLETED status means the backend actually works.

## Acceptance criteria

- [ ] Ordered checks. A failing check stops dependents (marked `skipped`), and independent ones still run:

| # | Check | Command (in sandbox) | Depends on |
|---|---|---|---|
| 1 | `syntax` | `python -m compileall -q src tests` | – |
| 2 | `lint` | `ruff check --output-format json .` (+ `ruff format --check`) | – |
| 3 | `deps` | `uv pip install -r requirements.txt -r requirements-dev.txt` → `uv pip check` | – |
| 4 | `startup` | `python -c "from src.main import app"` + `fastapi run src/main.py` and `GET /health` | 1, 3 |
| 5 | `migration` | `make mghead` → `alembic check` (no drift) → `alembic downgrade base` → `make mghead` | 3 |
| 6 | `conventions` | fastapi-skills checker (AST): use cases import no `infrastructure.models` / `sqlmodel`; domain entities are pure Pydantic; write use cases have `@Transactional`; no raw `HTTPException` in use cases; every model is imported in `modules/__init__.py`; every router is in `routers.py`; repos export `I<Name>RepoDep` and use cases `<Action>UsecaseDep`; DTOs have `to_entity()`; a rate limiter is attached | 1 |
| 7 | `tests` | `pytest -q --junitxml=reports/junit.xml` (skipped if `runTests=false`) | 4, 5 |
| 8 | `openapi` | `with TestClient(app): app.openapi()` (the lifespan must run, because the template registers routers there) → `openapi.json`, validated with `openapi-spec-validator`, operationId parity with the plan | 4 |

- [ ] Each check writes a `validation_runs` row and emits a `validation.check` event (status, duration, short summary).
- [ ] The `conventions` checker is a module of the agent (`orchestrator/checks/conventions.py`), run against the
      workspace from the worker (static analysis only, no code execution). Each violation → `{file, line, rule, hint}`,
      with the hint quoting the skill rule it breaks.
- [ ] Structured failure extraction: ruff JSON → `{file, line, code, message}`; pytest junit → failing test ids +
      assertion and traceback excerpt; Python tracebacks → file and line frames inside `/work`.
- [ ] Node output: `state.validation`, `state.failed_checks`, `failure_digest_ref` (max 30 KB, the most relevant first).
- [ ] Re-validation after repair runs failed checks + all dependents + `tests` (regression).
