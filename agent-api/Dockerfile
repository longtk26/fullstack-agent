FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .


FROM base AS api

RUN useradd --create-home --uid 10001 app
USER app

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && fastapi run src/main.py --host 0.0.0.0 --port 8000"]


FROM base AS worker

ARG CLAUDE_CODE_VERSION=2.1.309

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=docker:29-cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=node:22-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node:22-slim /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && npm install -g "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" \
    && npm cache clean --force

# Pinned base template for generated backends (Story 5.2) and the skill handed to the engine (Story 3.4).
RUN set -eu; . /app/templates/template.lock; \
    git clone --quiet --branch "$branch" "$repo" /opt/bga/fastapi-template; \
    git -C /opt/bga/fastapi-template checkout --quiet "$commit"; \
    rm -rf /opt/bga/fastapi-template/.git
COPY --from=skills fastapi-skills /opt/bga/skills/fastapi-skills

# Runs as root: it drives the host Docker socket for sandbox and preview containers (accepted local-only risk, Story 11.3).
CMD ["python", "-m", "src.worker"]
