# Story 13.2 — Base frontend: pinned Next.js + overlay, API client & mock layer

**Epic:** [13 — Frontend generation](epic13_frontend_generation.md) · **Requirements:** FR-25 · **Depends on:** 13.1 · **Decision:** Q11 (`pnpx create-next-app` per nextjs-skills)

## User story

As the frontend lane, I want every frontend to start from the same pinned, skill-conformant base with the API
client and mocks already wired, so that the engine only writes pages and components.

## Acceptance criteria

- [ ] Base project pinned by lock file (Next.js, React, shadcn style, pnpm version) and created the way
      nextjs-skills prescribes; our overlay adds layout primitives, providers (React Query, theme), the runtime
      config, the API client wrapper, test setup (Vitest + Playwright), ESLint config, Dockerfile(s) and README.
      Drift detection like 5.2 (`FRONTEND_TEMPLATE_DRIFT`).
- [ ] The `nextjs-skills` skill is installed into the workspace for the engine (`.claude/skills/` for Claude Code,
      `.agents/skills/` for Antigravity, as 3.4 does for `fastapi-skills`), and the project rules (`CLAUDE.md` /
      `AGENTS.md`) tell the engine to follow it; the frontend `conventions` check (13.4) enforces its checklist.
- [ ] Theme: `globals.css` tokens written from the plan (no hard-coded colours anywhere else).
- [ ] `dynamic` mode only:
  - contract types generated with `openapi-typescript` into `src/lib/api/schema.d.ts`; a typed fetch client
    (`src/lib/api/client.ts`) using `API_BASE_URL`;
  - MSW handlers + example data generated from the contract examples into `src/mocks/` (list endpoints honour
    `limit/offset/sort/filters`; writes keep an in-memory store);
  - `src/lib/runtime-config.ts`: the browser loads `{ mockApi, apiBaseUrl }` from a tiny route handler that
    reads `MOCK_TEST_API` and `API_BASE_URL` from the server environment, so switching needs a restart, not a
    rebuild; MSW starts only when `mockApi` is true.
- [ ] `static` mode: no client, no mocks, `output: "export"`; content from `FrontendSpec.content` is written to
      `src/content/*.json`.
- [ ] Commit `node:frontend_scaffold`.
