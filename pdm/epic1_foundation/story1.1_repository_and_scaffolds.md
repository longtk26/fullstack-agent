# Story 1.1 — Repository & service scaffolds

**Epic:** [1 — Foundation](epic1_foundation.md) · **Requirements:** §2, §3.1, NFR 8.4

## User story

As a developer, I want the agent API and UI scaffolded from our skill templates so that every
later story follows the same conventions from day one.

## Acceptance criteria

- [x] `git init` at repo root (branch `main`), with a `.gitignore` covering `.env`, `.data/`, `.venv`, `node_modules`, `.next`. *(done 2026-10-23)*
- [ ] `agent-api/` is cloned from `longtk26/template-frameworks` branch `feat/fastapi` as described in
      fastapi-skills. Template `.git` is removed. The app boots and `GET /health` returns 200.
- [ ] The template's gaps are fixed for the agent itself too: logger and error codes filled, rate limiting, CORS for
      the UI origin, and pytest + ruff set up. The same fixes as the generated-backend overlay (5.2), shared where practical.
- [ ] `agent-api` adds dependencies: `langgraph`, `langgraph-checkpoint-postgres`, `langchain-core`,
      `langsmith`, `redis`, `docker` (Docker SDK), `sse-starlette`, `psycopg[binary,pool]`.
- [ ] `src/worker.py` entrypoint exists and starts an idle loop for now (Epic 4 fills it in).
- [ ] `agent-ui/` is created with `pnpx create-next-app@latest` (App Router, TS, Tailwind, `src/`),
      shadcn initialised. `/` renders an empty app shell.
- [ ] `examples/specs/task-management.json` contains the requirements §5 example. A second example `examples/specs/two-entity.json`
      has ≥ 2 related entities (needed for the DoD in §10).
- [ ] `json.json` moved to `examples/frontend/revue-de-mode.json` as the reference fixture for Story 2.5.
- [ ] `agent-api/templates/template.lock` pins the `feat/fastapi` commit (currently `69e0231`) used for **generated**
      backends (5.2). It can be bumped independently of the agent's own scaffold.
- [ ] Root `Makefile` targets: `up`, `down`, `dev`, `logs`, `test`, `lint`, `migrate`.

## Technical notes

- API and worker share one codebase and image, with different commands. This keeps the domain
  models and repositories in one place.
- `engines/`, `orchestrator/` and `sandbox/` are infrastructure adapters in hexagonal terms. Use
  cases depend on ports (`ICodeEngine`, `ISandboxRunner`, `IJobQueue`), never on concrete classes.
