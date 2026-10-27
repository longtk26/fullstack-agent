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
# Antigravity CLI is a Go binary; its install script always takes "latest", so the release is pinned here
# (from https://antigravity-cli-auto-updater-974169037036.us-central1.run.app/manifests/linux_amd64.json).
ARG ANTIGRAVITY_VERSION=1.4.6
ARG ANTIGRAVITY_URL=https://storage.googleapis.com/antigravity-public/antigravity-cli/1.4.6-4884751325200384/linux-x64/cli_linux_x64.tar.gz
ARG ANTIGRAVITY_SHA512=4e1244b8b8c1280552f59c1b24b76a9245db9c80032aec6db28fb86033d6088abc30a90dad432d2b246c28fdd87d82abb48727d5ff88ba1d5d4ec76b33348e7d

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

RUN set -eu; cd /tmp; \
    curl -fsSL -o agy.tar.gz "$ANTIGRAVITY_URL"; \
    echo "$ANTIGRAVITY_SHA512  agy.tar.gz" | sha512sum -c -; \
    tar -xzf agy.tar.gz antigravity; \
    install -m 0755 antigravity /usr/local/bin/agy; \
    rm -f agy.tar.gz antigravity; \
    agy --version

COPY --from=docker:29-cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=node:22-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node:22-slim /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && npm install -g "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" \
    && npm cache clean --force

# Pinned base template for generated backends (Story 5.2) and the skills handed to the engine (Stories 3.4, 13.2).
RUN set -eu; . /app/templates/template.lock; \
    git clone --quiet --branch "$branch" "$repo" /opt/bga/fastapi-template; \
    git -C /opt/bga/fastapi-template checkout --quiet "$commit"; \
    rm -rf /opt/bga/fastapi-template/.git
COPY --from=skills fastapi-skills /opt/bga/skills/fastapi-skills
COPY --from=skills nextjs-skills /opt/bga/skills/nextjs-skills

# Runs as root: it drives the host Docker socket for sandbox and preview containers (accepted local-only risk, Story 11.3).
CMD ["python", "-m", "src.worker"]
