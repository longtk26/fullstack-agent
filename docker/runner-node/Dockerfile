# bga-runner-node: validates generated Next.js frontends (Story 13.4). Built with `make runner-node`.
# Build context: agent-api/templates/nextjs_base (its lock file pre-warms the pnpm store, so a generated frontend
# installs offline). The sandbox mounts the named volume `bga-pnpm-store-<base lock key>` at /pnpm-store; Docker
# fills an empty volume from this image's /pnpm-store on first use, so a new base lock gets a new, filled volume.
FROM node:22-bookworm-slim

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    npm_config_store_dir=/pnpm-store \
    NEXT_TELEMETRY_DISABLED=1 \
    CI=1

RUN npm install -g pnpm@10.18.3 && npm cache clean --force

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml /opt/bga/fe-base/
RUN cd /opt/bga/fe-base \
    && pnpm fetch --frozen-lockfile \
    && pnpm install --frozen-lockfile --offline \
    && pnpm exec playwright install --with-deps chromium \
    && rm -rf node_modules /root/.cache \
    && chmod -R a+rwX /pnpm-store /ms-playwright

RUN useradd --uid 10001 --no-create-home runner
ENV HOME=/tmp
USER 10001
WORKDIR /work
