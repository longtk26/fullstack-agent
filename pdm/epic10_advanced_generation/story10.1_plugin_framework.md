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

- [ ] A plugin is added by a `templates/plugins/<name>/` folder and one class, with no change elsewhere in codegen.
- [ ] The six hook points exist and are covered by tests; plugin files are owned and checked by `conventions`.
- [ ] The context pack lists the active plugins' APIs.
- [ ] Integrations without a plugin produce the stub and an `unresolved` entry.
- [ ] Moving the rate limiter into a plugin changes no generated file (snapshots unchanged).

## Verify

`make lint`, `make test`, `BGA_SANDBOX_TESTS=1 make test`; `make up` and generate `two-entity` and `shop` with the fake
engine; both pass validation as before.

## Status

**Planned (2026-11-04).**
