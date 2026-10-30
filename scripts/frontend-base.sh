#!/bin/sh
# Recreates the pinned Next.js base every generated frontend starts from (Story 13.2, decision Q11):
# `create-next-app` exactly as the nextjs-skills skill prescribes, shadcn/ui (base-nova) with every primitive of
# the FrontendSpec catalogue, the libraries the skill mandates, and the bundled fonts (Story 17.7). Runs inside node:22 so the result does not
# depend on the host; the lock file pins every version. Output: agent-api/templates/nextjs_base/ (no node_modules).
#
#   make frontend-base        # review the diff, then update agent-api/templates/nextjs_overlay/overlay.json
set -eu
NEXT_VERSION=16.4.2
SHADCN_VERSION=4.22.1
PNPM_VERSION=10.18.3
MSW_VERSION=2.12.4
OUT=/out
PRIMITIVES="$1"
FONTS="$2"

corepack enable >/dev/null 2>&1
corepack prepare "pnpm@$PNPM_VERSION" --activate >/dev/null 2>&1
cd /tmp
CI=1 pnpm dlx "create-next-app@$NEXT_VERSION" base --typescript --tailwind --eslint --app --src-dir \
  --import-alias "@/*" --use-pnpm --yes --disable-git --no-agent-feedback --skip-install
cd base
pnpm pkg set packageManager="pnpm@$PNPM_VERSION"
pnpm install
pnpm dlx "shadcn@$SHADCN_VERSION" init -b base -p nova -y --no-monorepo --force
# shellcheck disable=SC2086
pnpm dlx "shadcn@$SHADCN_VERSION" add -y --overwrite $PRIMITIVES
pnpm add -E @tanstack/react-query zustand react-hook-form zod @hookform/resolvers next-themes
# shellcheck disable=SC2086
pnpm add -E $FONTS
pnpm add -E -D @types/node@22 "msw@$MSW_VERSION" vitest @vitejs/plugin-react jsdom @testing-library/react \
  @testing-library/jest-dom @testing-library/user-event @playwright/test vite-tsconfig-paths
pnpm exec msw init public --no-save
cat > base.lock <<LOCK
nextVersion=$NEXT_VERSION
shadcnVersion=$SHADCN_VERSION
shadcnStyle=base-nova
pnpmVersion=$PNPM_VERSION
node=$(node --version)
createdWith=pnpm dlx create-next-app@$NEXT_VERSION --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-pnpm
LOCK
rm -rf "$OUT"/* "$OUT"/.[!.]* 2>/dev/null || true
tar --exclude=node_modules --exclude=.next -cf - . | tar -xf - -C "$OUT"
