-include .env
export

COMPOSE     := docker compose
COMPOSE_DEV := docker compose -f docker-compose.yml -f docker-compose.dev.yml
API_DIR     := agent-api
UI_DIR      := agent-ui
PY          := $(CURDIR)/$(API_DIR)/.venv/bin

BGA_API_PORT   ?= 8100
BGA_UI_PORT    ?= 3100
BGA_PG_PORT    ?= 5442
BGA_REDIS_PORT ?= 6389

# Host-side overrides for running api/worker/ui outside Docker.
DEV_ENV := DB_URL=postgresql+psycopg://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@localhost:$(BGA_PG_PORT)/$(POSTGRES_DB) \
           REDIS_URL=redis://localhost:$(BGA_REDIS_PORT)/0 \
           CORS_ORIGINS=http://localhost:$(BGA_UI_PORT) \
           WORKSPACE_ROOT=$(HOST_WORKSPACE_ROOT) \
           WORKER_HEARTBEAT_FILE=$(CURDIR)/.data/worker.heartbeat \
           ENGINE_SKILLS_DIR=$(CURDIR)/.agents/skills \
           CLAUDE_CREDENTIALS_FILE=$(CLAUDE_CREDENTIALS_HOST_FILE)

.PHONY: env up down down-all ps logs dev dev-down dev-api dev-worker dev-ui setup migrate test lint

env:
	@test -f .env && echo ".env already exists" || ( \
	  sed -e "s|^JWT_SECRET=.*|JWT_SECRET=$$(openssl rand -hex 32)|" \
	      -e "s|^HOST_WORKSPACE_ROOT=.*|HOST_WORKSPACE_ROOT=$(CURDIR)/.data/workspaces|" \
	      .env.example > .env && mkdir -p .data/workspaces && echo "created .env" )

up: env
	$(COMPOSE) up -d --build --wait

down:
	$(COMPOSE) down

down-all:
	$(COMPOSE) down -v --remove-orphans

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f --tail=200

dev: env
	$(COMPOSE_DEV) up -d --wait postgres redis

dev-down:
	$(COMPOSE_DEV) down

setup:
	cd $(API_DIR) && uv venv -q -p 3.12 .venv && uv pip install -q -p .venv/bin/python -r requirements-dev.txt
	cd $(UI_DIR) && pnpm install

dev-api:
	cd $(API_DIR) && $(DEV_ENV) $(PY)/fastapi dev src/main.py --port $(BGA_API_PORT)

dev-worker:
	cd $(API_DIR) && $(DEV_ENV) $(PY)/python -m src.worker

dev-ui:
	cd $(UI_DIR) && API_URL=http://localhost:$(BGA_API_PORT) pnpm dev --port $(BGA_UI_PORT)

migrate:
	cd $(API_DIR) && $(DEV_ENV) $(PY)/alembic upgrade head

test:
	cd $(API_DIR) && $(DEV_ENV) $(PY)/pytest

lint:
	cd $(API_DIR) && $(PY)/ruff check . && $(PY)/ruff format --check .
	cd $(UI_DIR) && pnpm lint
