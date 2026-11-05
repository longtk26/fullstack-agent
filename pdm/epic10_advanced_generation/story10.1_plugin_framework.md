# Story 10.1 — Plugin framework

**Epic:** [10 — Advanced generation](epic10_advanced_generation.md) · **Requirements:** FR-34 · **Depends on:** 18.13, 10.0b

## User story

As a maintainer, I want each backend feature to be a plugin with a fixed shape, so that adding auth, files, jobs or
payments does not grow `backend/codegen.py` into one large special case per feature, and the engine knows which
APIs the project already has.

## Steps

1. **Plugin class and registry** (`orchestrator/plugins/`): `applies(spec)`, plan and contract additions, files
   (`templates/plugins/<name>/backend/files`, `frontend/files`, filled in by 22.7), requirements, env vars
   (`.env.ex` and the manifest `env`), owned paths (`scaffold.add_owned`), smoke checks, manifest entry, engine note. Plugins are ordered by
   declared dependencies; a cycle or a missing dependency is a planner error.
2. **Six hook points** in `backend/codegen.py`, each a list of contributions rendered in a fixed order:
   router parameters, use-case pre-checks, use-case events (outbox, 10.6), repository filters, response fields,
   app and worker startup. Output stays a pure function of (spec, plan) and byte-identical between runs.
3. **Engine notes:** each active plugin's API note goes into the `complete_backend` context pack (18.13) under
   "Already in this project", with the files the engine must not edit.
4. **Fallback for integrations without a plugin** (was story 10.4): an output port in `ports/output/` and an adapter
   stub in `infrastructure/adapters/<name>_adapter.py` raising `NotImplementedError`, its env vars in `.env.ex`, and an
   `unresolved` entry with `specPath` and reason; the generation can still be COMPLETED.
5. **Proof with no behaviour change:** the rate limiter (`src/libs/rate_limit/`, today in the overlay) becomes the
   `rate-limit` plugin; the generated projects of every example are byte-identical before and after.
6. **Manifest:** `plugins: [{name, version}]` (7.1).
7. **Tests:** registry ordering, each hook point, snapshot of a plugin combination on a golden spec, the fallback
   stub, the rate-limit proof.

## Acceptance criteria

- [x] A plugin is added by a `templates/plugins/<name>/` folder and one class, with no change elsewhere in codegen.
- [x] The six hook points exist and are covered by tests; plugin files are owned and checked by `conventions`.
- [x] The context pack lists the active plugins' APIs.
- [x] Integrations without a plugin produce the stub and an `unresolved` entry.
- [x] Moving the rate limiter into a plugin changes no generated file (snapshots unchanged).

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test`; `make up` and generate `two-entity` and `shop` with the fake
engine; both pass validation as before.

## Status

**Done (2026-11-05)** on `feat/epic10-backend-plugins`, under the user's review.

- **Framework** (`orchestrator/plugins/`): `base.py` (the `Plugin` class and the contribution types `RouterParam`,
  `Code`, `RepositoryFilter`, `ResponseField`, `AppStartup`, `Setting`), the registry with dependency order
  (`ordered`; a cycle or a missing plugin is a `PluginError`, raised by the planner), `active_plugins(spec)`,
  `plan_plugins(plan)`. The planner records `plan["plugins"]` (`{name, version}`, also in the manifest and
  `.bga/scaffold.json`) and lets each plugin add to the plan.
- **Scaffold** (`plugins/app.py`, called by `scaffold_project(..., plan=)`): the plugins' `backend/files`, `src/main.py`
  rendered from the app-startup hook (imports, setup before CORS, exception handlers, lifespan lines), their settings
  in place of the overlay's `# {{PLUGIN_SETTINGS}}` line of `config.py` and in `.env.ex`, their requirements. Without
  a plan: the plugins every project has, so every caller of `scaffold_project` still gets a working app.
- **Hook points in codegen**: router parameters (handler and use case; a list's go before its query parameters),
  use-case pre-checks (after the record is loaded; delete loads it only when a plugin needs it), use-case events
  (after the write), repository filters (an optional `list` parameter, its `where`, and the value the list use case
  passes), response fields; app startup in `main.py`; `worker_startup` is collected (`plugins.app.worker_startup`) for
  10.6 to render.
- **Engine notes**: the context pack gains "Already in this project", with each active plugin's note and the files
  not to edit.
- **Integrations without a plugin** (`integration-stubs`): `src/modules/integrations/ports/output/<name>_port.py`, a
  stub adapter raising `NotImplementedError` with its `I<Name>PortDep`, `<NAME>_BASE_URL` / `<NAME>_API_KEY` settings
  and `.env.ex` lines, and an `unresolved` entry with `specPath`; not generator-owned, so the engine or a developer
  fills it in.
- **The proof**: the rate limiter is the `rate-limit` plugin (`templates/plugins/rate-limit`: the limiter and the 429
  handler, a setting, middleware and handler through the app-startup hook). The codegen snapshots of every example
  are unchanged; the plan snapshots gain `plugins`.
- **Tests**: `tests/test_plugins.py` (10): plugins named in plans, ordering, cycle and missing errors, the rate
  limiter scaffolded with no plan, a plan's plugins scaffolded, each hook point landing where it should with a test
  plugin (`HookProbePlugin`, listed in `docs/development/test-doubles.md`), a module no plugin touches unchanged, the
  integration stubs, the engine note.

**Deviations:**

- `src/main.py` is no longer an overlay file but rendered; it differs from the old one only in importing the 429
  handler from `src.libs.rate_limit` (the handler moved into the plugin; `exceptions.handlers._error` became the
  public `error_response` for it).
- `slowapi` stays in the overlay's base `requirements.txt` and a plugin adds only what the base lacks: the sandbox's
  baked venv (`docker/runner`) matches the base file byte for byte, and the first try (slowapi only in the plugin)
  failed every real sandbox startup. Plugins with new libraries (10.2's PyJWT and argon2, 10.5's boto3) need a decision
  then: bake them into the runner image's venv, or accept a venv install per project.
- The worker-startup hook is defined and collected, not rendered: the worker arrives with 10.6.

**Verified:** `make lint`; `tests/test_plugins.py`, the codegen, planner, contract, scaffold and integration-contract
tests; `BGA_SANDBOX_TESTS=1` for `tests/sandbox/test_sandbox_workflow.py` and `tests/sandbox/test_sandbox_pipeline.py`
(10 tests, real sandbox: the rendered `main.py` starts, template tests and smoke scenarios pass); `make test`: all
pass. `make up`, then a fake-engine `flashcards-dynamic` generation (`gen_01M6MV8FTHMN3P58YFJWBB4CD0`): COMPLETED in
162 s, all three lanes completed, `.bga/scaffold.json` lists `rate-limit@1`, "app starts and GET /health → 200", 38
template tests and 21 scenarios pass; the live preview answers 125 quick requests with 119 × 200 and 6 × 429.

**Found, not changed (follow-up):** the 429 body is SlowAPI's own `{"error": "Rate limit exceeded: …"}`, not the
API's error envelope: its middleware never reaches our `RateLimitExceeded` handler. The old `main.py` behaves the same
(checked on a project scaffolded before this story), so this has been true since 5.4; worth fixing in the
`rate-limit` plugin with 10.2's stricter login limits.
