# Story 13.2 — Base frontend: pinned Next.js + overlay, API client & mock layer

**Epic:** [13 — Frontend generation](epic13_frontend_generation.md) · **Requirements:** FR-25 · **Depends on:** 13.1 · **Decision:** Q11 (`pnpx create-next-app` per nextjs-skills)

## User story

As the frontend lane, I want every frontend to start from the same pinned, skill-conformant base with the API
client and mocks already wired, so that the engine only writes pages and components.

## Acceptance criteria

- [x] Base project pinned by lock file (Next.js, React, shadcn style, pnpm version) and created the way
      nextjs-skills prescribes; our overlay adds layout primitives, providers (React Query, theme), the runtime
      config, the API client wrapper, test setup (Vitest + Playwright), ESLint config, Dockerfile(s) and README.
      Drift detection like 5.2 (`FRONTEND_TEMPLATE_DRIFT`).
- [x] The `nextjs-skills` skill is installed into the workspace for the engine (`.claude/skills/` for Claude Code,
      `.agents/skills/` for Antigravity, as 3.4 does for `fastapi-skills`), and the project rules (`CLAUDE.md` /
      `AGENTS.md`) tell the engine to follow it; the frontend `conventions` check (13.4) enforces its checklist.
- [x] Theme: `globals.css` tokens written from the plan (no hard-coded colours anywhere else).
- [x] `dynamic` mode only:
  - contract types generated with `openapi-typescript` into `src/lib/api/schema.d.ts`; a typed fetch client
    (`src/lib/api/client.ts`) using `API_BASE_URL`;
  - MSW handlers + example data generated from the contract examples into `src/mocks/` (list endpoints honour
    `limit/offset/sort/filters`; writes keep an in-memory store);
  - `src/lib/runtime-config.ts`: the browser loads `{ mockApi, apiBaseUrl }` from a tiny route handler that
    reads `MOCK_TEST_API` and `API_BASE_URL` from the server environment, so switching needs a restart, not a
    rebuild; MSW starts only when `mockApi` is true.
- [x] `static` mode: no client, no mocks, `output: "export"`; content from `FrontendSpec.content` is written to
      `src/content/*.json`.
- [x] Commit `node:frontend_scaffold`.

**Status (2026-10-27):** done. Base `agent-api/templates/nextjs_base/` (from `scripts/frontend-base.sh` /
`make frontend-base`: `create-next-app@16.4.2` with the skill's flags, shadcn 4.22.1 base-nova with every catalogue
primitive, React Query, Zustand, RHF, Zod, next-themes, MSW, Vitest, Playwright; pnpm 10.18.3; lock file
committed, no node_modules). Overlay `agent-api/templates/nextjs_overlay/` (`files/common`, `files/static`,
`files/dynamic`, `overlay.json`). Scaffold `src/orchestrator/frontend_scaffold.py`, generated code
`frontend_codegen.py`. Notes and deviations:
- Contract types are emitted by us (`src/lib/api/types.ts`, `T`-prefixed named types as the skill wants), not by
  `openapi-typescript` into `schema.d.ts`; the same pass generates one typed function per operation
  (`operations.ts`), React Query key factories and hooks (`query-keys.ts`, `queries.ts`) and one Zod schema +
  values type + defaults per FrontendSpec form (`src/lib/forms.ts`). All deterministic, no Node needed.
- Mock layer: generic MSW handlers (`src/mocks/handlers.ts`, overlay) driven by `operations.json` + the
  contract fixtures (`fixtures.json`); served under `/mock-api` so they never collide with page routes.
- Only the shadcn primitives the plan needs are copied; overlay, generated and shadcn files plus `package.json`
  and the lock file are generator-owned (`.bga/owned.json`), so the engine cannot add dependencies.
- The base's `use-mobile.ts` (shadcn sidebar) fails the React hooks lint rule; the overlay replaces it.
- The scaffold commit is `node:scaffold_frontend` (commits are named after nodes).
