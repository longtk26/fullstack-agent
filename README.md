# Backend Generation Agent

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

- UI: http://localhost:3100 · API docs: http://localhost:8100/docs
- Log in: `curl -s localhost:8100/api/v1/auth/login -H 'content-type: application/json' -d '{"email":"admin@bga.local","password":"admin12345"}'`
  (users come from `SEED_USERS` in `.env`)

`make down` stops the stack; `make down-all` also removes volumes.

## Develop

```bash
make setup                         # agent-api venv (uv) + agent-ui deps (pnpm)
make dev                           # postgres + redis only, on ports 5442 / 6389
make migrate
make dev-api   # :8100   make dev-worker   make dev-ui   # :3100
make test && make lint
```
