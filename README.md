# Fullstack Generation Agent

Turns a requirement, a Frontend-Agent site JSON, or a BackendSpec JSON into a tested FastAPI backend, then runs
it as its own container. Requirements: [requirements.md](requirements.md) · Backlog: [pdm/](pdm/README.md)

| Path | What |
|---|---|
| `agent-api/` | FastAPI API + LangGraph worker (one image, two targets), built on `.agents/skills/fastapi-skills` |
| `agent-ui/` | Next.js UI, built on `.agents/skills/nextjs-skills` |
| `examples/` | Sample BackendSpecs and a sample frontend site JSON |

## Run (verify)

```bash
make env   # first time: creates .env with a random JWT_SECRET and the workspace path
make up    # builds and starts postgres 18, redis, agent-api, agent-worker, agent-ui; waits until healthy
make ps
```

- UI: http://localhost:3100. Sign in with a seeded user from `SEED_USERS` in `.env` (for example
  `user@bga.local` / `user12345`), then **New generation** → JSON tab → *Load example* `two-entity` → pick the
  **Fake** engine to watch a scripted run without model calls. The fake engine is a test double that only fits that
  example; see [docs/development/test-doubles.md](docs/development/test-doubles.md).
- API docs: http://localhost:8100/docs. API login:
  `curl -s localhost:8100/api/v1/auth/login -H 'content-type: application/json' -d '{"email":"admin@bga.local","password":"admin12345"}'`

Engines (default models: `claude-sonnet-5-5` and `gemini-3.8-flash-medium`; override with `CLAUDE_CODE_MODEL` /
`ANTIGRAVITY_MODEL`): **Claude Code** runs in the Docker worker (an `ANTHROPIC_API_KEY`, or your subscription login via
`CLAUDE_CREDENTIALS_HOST_FILE`). **Antigravity** with `ANTIGRAVITY_AUTH=account` (your `agy` Google login) needs the
desktop keyring, which containers cannot reach, so `make up` also starts a host worker for Antigravity jobs only
(needs `uv` and `agy` on the host; log in `.data/host-worker.log`). With `GEMINI_API_KEY` or ADC it runs in Docker.

Tracing: every generation has a **Trace** tab (span waterfall: nodes, engine runs, model calls, tools, checks,
sandbox commands) and **Usage & traces** (`/usage`) sums time, model calls, tokens and cost per period. Claude Code
reports its cost; Antigravity's is *estimated* from list prices (`MODEL_PRICES` overrides them). Set
`LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` to also send each generation to LangSmith as one trace, to
`LANGSMITH_PROJECT` or, with `LANGSMITH_AGENT_ID`, to that agent's environment (beta, enabled per workspace).

Modes (Epics 12, 13): `POST /api/v1/generations` takes `mode: backend | static | dynamic`. `static` takes a
FrontendSpec (`examples/frontend-specs/`, schema at `GET /api/v1/frontend-specs/schema`) and builds a Next.js
static site; `dynamic` takes a FrontendSpec and a BackendSpec, checks that every page binding and form exists in
the API contract derived from the BackendSpec, then generates the backend against that contract and a Next.js app
that talks to it through a generated client (with a mock API until the backend is wired in, Epic 14). Frontends
start from a pinned `create-next-app` base (`agent-api/templates/nextjs_base`, rebuilt with `make frontend-base`)
plus an overlay, follow `nextjs-skills`, and are validated in a Node sandbox (`bga-runner-node`, built by
`make up`: install, typecheck, lint, conventions, build, routes, Vitest + Playwright). A finished frontend runs as
its own preview container (**Open site** on the generation page). Sample requirements: `examples/requirements/`.

`make down` stops the stack (and the host worker, and preview containers); `make down-all` also removes volumes.

## Develop

```bash
make setup                         # agent-api venv (uv) + agent-ui deps (pnpm)
make dev                           # postgres + redis only, on ports 5442 / 6389
make migrate
make dev-api   # :8100   make dev-worker   make dev-ui   # :3100
make test && make lint
```
