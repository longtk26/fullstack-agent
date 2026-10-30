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
# Antigravity CLI is a Go binary; its install script always takes "latest", so the release is pinned here per
# architecture (from https://antigravity-cli-auto-updater-974169037036.us-central1.run.app/manifests/linux_<arch>.json).
# arm64 is for Apple Silicon hosts: an x64 binary cannot run there (no x86-64 loader for Rosetta in this image).
ARG TARGETARCH
ARG ANTIGRAVITY_VERSION=1.4.6
ARG ANTIGRAVITY_BASE_URL=https://storage.googleapis.com/antigravity-public/antigravity-cli/1.4.6-4884751325200384
ARG ANTIGRAVITY_SHA512_AMD64=4e1244b8b8c1280552f59c1b24b76a9245db9c80032aec6db28fb86033d6088abc30a90dad432d2b246c28fdd87d82abb48727d5ff88ba1d5d4ec76b33348e7d
ARG ANTIGRAVITY_SHA512_ARM64=0daa84244922bd648f940d44dfc33ace8c26217cd710ff116902eb8708829a0cfe70640f0d6b480243442881c9aeb4a905a9aa7887dd8a70159aa0f1a4f98a8f

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

RUN set -eu; cd /tmp; \
    case "${TARGETARCH:-amd64}" in \
      amd64) path=linux-x64/cli_linux_x64.tar.gz; sha="$ANTIGRAVITY_SHA512_AMD64" ;; \
      arm64) path=linux-arm/cli_linux_arm64.tar.gz; sha="$ANTIGRAVITY_SHA512_ARM64" ;; \
      *) echo "unsupported architecture: $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    curl -fsSL -o agy.tar.gz "$ANTIGRAVITY_BASE_URL/$path"; \
    echo "$sha  agy.tar.gz" | sha512sum -c -; \
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
# Example specs: references for requirement drafting and the fake engine's draft fixtures (Stories 2.4, 12.4).
COPY --from=examples . /opt/bga/examples

# Runs as root: it drives the host Docker socket for sandbox and preview containers (accepted local-only risk, Story 11.3).
CMD ["python", "-m", "src.worker"]
