# Story 13.4 — Frontend validation & repair (Node sandbox)

**Epic:** [13 — Frontend generation](epic13_frontend_generation.md) · **Requirements:** FR-25, FR-11, FR-12 · **Depends on:** 13.3, 6.1

## User story

As a user, I want the generated frontend to build, type-check and pass its tests for real before it is marked
done, like the backend.

## Acceptance criteria

- [x] `bga-runner-node` image (Node 22, pnpm, Playwright Chromium, a pnpm store pre-warmed with the base
      dependencies) used through the same sandbox port as 6.1 (internal network, read-only rootfs, limits).
- [x] Ordered checks with dependencies, reported like 6.2: `install` (offline from the store, egress only for
      new packages) → `typecheck` (`tsc --noEmit`) → `lint` (ESLint) → `conventions` (static nextjs-skills checker:
      named React imports, `T` prefix types, no `localStorage` tokens, no hard-coded colours, components > 30
      logic lines have a hook, only the generated client calls the network, owned files unchanged) → `build`
      (`next build`) → `routes` (every planned route exists in the build output) → `tests` (Vitest + Playwright
      smoke on the mock layer; `static`: against the export).
- [x] Failures feed the same repair loop (prompt `repair_frontend`), max attempts from options.

**Status (2026-10-27):** done. `docker/runner-node/Dockerfile` (`make runner-node`, part of `make up`),
`src/orchestrator/frontend_validation.py`, `checks/frontend_conventions.py`, node `validate_frontend` /
`repair_frontend` (prompt `repair_frontend/v1`). Notes and deviations:
- The pre-warmed pnpm store reaches the sandbox as the named volume `bga-pnpm-store` (filled from the image on
  first use); `install` runs `--offline` and only falls back to the egress network when the lock file needs new
  packages. Measured: install 31 s, the whole pipeline about 100 s per attempt.
- Frontend sandbox: 2 CPUs, 3 GB, 1 GB `/tmp`, no database; its containers and network carry a part label so the
  backend and frontend sandboxes of one job never remove each other.
- `build` depends on `install` and `typecheck`; `tests` runs `vitest run` and `playwright test` (dynamic: `next
  start` on the mock API; static: a small static server over `out/`). Check results are stored as
  `frontend:<check>`. Frontend repairs have their own counter (`frontend_repair_attempts`), limit
  `maxRepairAttempts`.
- Opt-in Docker tests: `tests/sandbox/test_frontend_sandbox.py` (golden site passes all 7 checks offline; a type
  error fails `typecheck` and skips `build`).
