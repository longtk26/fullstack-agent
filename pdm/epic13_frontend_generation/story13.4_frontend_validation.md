# Story 13.4 — Frontend validation & repair (Node sandbox)

**Epic:** [13 — Frontend generation](epic13_frontend_generation.md) · **Requirements:** FR-25, FR-11, FR-12 · **Depends on:** 13.3, 6.1

## User story

As a user, I want the generated frontend to build, type-check and pass its tests for real before it is marked
done, like the backend.

## Acceptance criteria

- [ ] `bga-runner-node` image (Node 22, pnpm, Playwright Chromium, a pnpm store pre-warmed with the base
      dependencies) used through the same sandbox port as 6.1 (internal network, read-only rootfs, limits).
- [ ] Ordered checks with dependencies, reported like 6.2: `install` (offline from the store, egress only for
      new packages) → `typecheck` (`tsc --noEmit`) → `lint` (ESLint) → `conventions` (static nextjs-skills checker:
      named React imports, `T` prefix types, no `localStorage` tokens, no hard-coded colours, components > 30
      logic lines have a hook, only the generated client calls the network, owned files unchanged) → `build`
      (`next build`) → `routes` (every planned route exists in the build output) → `tests` (Vitest + Playwright
      smoke on the mock layer; `static`: against the export).
- [ ] Failures feed the same repair loop (prompt `repair_frontend`), max attempts from options.
