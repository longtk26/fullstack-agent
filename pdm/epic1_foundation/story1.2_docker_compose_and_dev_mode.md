# Story 1.2 — Docker Compose stack & dev mode

**Epic:** [1 — Foundation](epic1_foundation.md) · **Requirements:** §2, NFR 8.1, 8.2 · **Depends on:** 1.1

## User story

As the operator, I want to start the whole system with `docker compose up` to verify it, and as a
developer I want a lighter dev mode with hot reload.

## Acceptance criteria

- [ ] `docker-compose.yml` services:
  - `postgres` (**18**, volume `pgdata` mounted at `/var/lib/postgresql`: the PG 18 image moved `PGDATA` to `/var/lib/postgresql/18/docker`, healthcheck). One DB `agent` holds app tables plus LangGraph checkpoint tables.
  - `redis` (7, healthcheck).
  - `agent-api`: `:8000`, depends on healthy postgres and redis, runs migrations on start.
  - `agent-worker`: same image, command `python -m src.worker`. Mounts `/var/run/docker.sock` and the workspace dir.
  - `agent-ui`: `:3000`, production build, `NEXT_PUBLIC_API_URL` / internal `API_URL`.
- [ ] Docker network `bga-net` for compose services. The worker creates a separate
      `bga-previews` network for preview containers (Epic 7).
- [ ] Worker image includes the Docker CLI, `claude` (Claude Code CLI) and `agy` (Antigravity CLI,
      version pinned after spike 3.3). It also includes the fastapi template checked out at the `template.lock` sha
      (`/opt/bga/fastapi-template`) and a copy of `.agents/skills/fastapi-skills`, so jobs never clone from GitHub at runtime.
- [ ] Workspace storage is a host bind mount `./.data/workspaces`, mounted at the **same absolute path** inside
      the worker (`HOST_WORKSPACE_ROOT`). Sibling sandbox containers can then bind the same path.
- [ ] `docker-compose.dev.yml` and `make dev` start only postgres and redis with ports published.
      `make dev-api`, `make dev-worker` and `make dev-ui` run on the host with reload.
- [ ] `.env.example` documents every variable: DB/Redis URLs, `JWT_SECRET`, `ANTHROPIC_API_KEY`,
      Antigravity credentials, `LANGSMITH_*`, `WORKER_CONCURRENCY`, `PREVIEW_PORT_RANGE`,
      `SANDBOX_CPU`, `SANDBOX_MEMORY`, `JOB_TIMEOUT_SECONDS`.
- [ ] `make up && make ps` shows all five services healthy on a clean machine.

## Technical notes

- Mounting the Docker socket gives root-equivalent access to the host. That is acceptable for the
  local MVP and is recorded as a known risk in 11.3. A later option is a `docker:dind` sidecar or sysbox.
- No secrets are baked into images. Everything comes from `.env`.

**Update (2026-10-26):** `docker-compose.dev.yml` was removed: the base compose file publishes Postgres and Redis
on `127.0.0.1` (5442, 6389), so host processes (dev servers, tests, the Antigravity host worker) work while the
full stack runs; `make dev` starts just those two services.
