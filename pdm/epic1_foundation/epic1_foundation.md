# Epic 1 — Foundation & local stack

## Overview

Build the base that every other epic runs on: the monorepo, the two app scaffolds (following the
project skills), a Docker Compose stack you can verify with one command, a dev mode for fast
iteration, the agent's own data model, and access control for generation jobs.

**Requirements:** §2 Technology Stack, §3.1, FR-14 (access control), NFR 8.1 / 8.2

## Repository layout (target)

```
backend-generation-agent/
├── agent-api/                 # FastAPI (fastapi-skills template) — API + worker share this codebase
│   ├── src/
│   │   ├── main.py            # API entrypoint
│   │   ├── worker.py          # worker entrypoint (Epic 4)
│   │   ├── modules/
│   │   │   ├── auth/  specs/  generations/  artifacts/  previews/  traces/  health/
│   │   │   └── shared/{domain/entities, infrastructure/models}
│   │   ├── orchestrator/      # LangGraph graph, state, nodes (Epic 4–6)
│   │   ├── engines/           # CodeEngine port + claude_code / antigravity / fake adapters (Epic 3)
│   │   ├── sandbox/           # Docker sandbox + preview runners (Epic 6–7)
│   │   └── libs/
│   ├── prompts/               # versioned prompt templates (3.4)
│   ├── templates/fastapi_overlay/     # files layered on top of the fastapi-skills template for generated projects (5.2)
│   ├── templates/template.lock        # pinned `feat/fastapi` commit sha of longtk26/template-frameworks
│   └── tests/
├── agent-ui/                  # Next.js (nextjs-skills)
├── docker/                    # sandbox runner image, compose helpers
├── examples/specs/            # sample BackendSpecs (task-management, two-entity, …)
├── examples/frontend/         # sample Frontend-Agent site JSON (json.json → revue-de-mode.json)
├── docker-compose.yml
├── .env.example
└── Makefile
```

## Stories

| # | Story | Depends on |
|---|---|---|
| 1.1 | [Repository & service scaffolds](story1.1_repository_and_scaffolds.md) | – |
| 1.2 | [Docker Compose stack & dev mode](story1.2_docker_compose_and_dev_mode.md) | 1.1 |
| 1.3 | [Agent data model & migrations](story1.3_agent_data_model.md) | 1.1 |
| 1.4 | [Agent API authentication & job ownership](story1.4_agent_auth_and_ownership.md) | 1.3 |

## Epic acceptance

- `make up` starts postgres, redis, agent-api, agent-worker and agent-ui, and all report healthy.
- `make dev` starts only infra in Docker. api, worker and ui run on the host with reload.
- A logged-in user can call `GET /api/v1/me`. Another user's resources return 404.
