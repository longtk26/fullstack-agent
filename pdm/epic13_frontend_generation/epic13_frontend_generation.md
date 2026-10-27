# Epic 13 — Frontend generation (Next.js on nextjs-skills)

## Overview

Generate the frontend described by a FrontendSpec with the same principle as the backend: **deterministic
foundation, LLM for the pages**. Every project starts from a pinned Next.js base following
`.agents/skills/nextjs-skills` (pnpm, App Router, shadcn/ui, design tokens, React Query, Zustand, RHF + Zod),
plus our overlay. The engine writes the pages and composite components; a Node sandbox builds and tests the
result; the repair loop fixes failures.

In `dynamic` mode the frontend talks to the backend only through a **typed client generated from the contract**
(12.3). A **mock layer** generated from the same contract (MSW handlers + example data) answers every call while
`MOCK_TEST_API=true`, so the frontend is built and tested without waiting for the backend (switch: 14.2).

**Requirements:** FR-25 (frontend generation), FR-26 (frontend preview) — requirements v1.2

## Generated frontend project

```
frontend/
├── src/app/                         # one route folder per FrontendSpec page (layout.tsx = the shell)
├── src/components/{ui,layout}/      # shadcn primitives (added by the planner) + layout primitives (overlay)
├── src/features/<page or domain>/   # engine: composite components, hooks (use-*.ts), query keys
├── src/lib/api/                     # overlay + generated: contract types (openapi-typescript), fetch client
├── src/mocks/                       # generated from the contract: MSW handlers + example data
├── src/lib/runtime-config.ts        # overlay: reads MOCK_TEST_API / API_BASE_URL at runtime (no rebuild to switch)
├── src/app/globals.css              # theme tokens from FrontendSpec.theme
├── tests/                           # Vitest component tests + Playwright smoke per page
└── Dockerfile  .env.ex  README.md   # static: nginx serving `next export`; dynamic: Node standalone server
```

## Stories

| # | Story | Depends on |
|---|---|---|
| 13.1 | [Frontend planner](story13.1_frontend_planner.md) | 12.1, 12.3 |
| 13.2 | [Base frontend: pinned Next.js + overlay, API client & mock layer](story13.2_base_frontend.md) | 13.1 |
| 13.3 | [Page & component generation](story13.3_page_generation.md) | 13.2, 3.2 |
| 13.4 | [Frontend validation & repair (Node sandbox)](story13.4_frontend_validation.md) | 13.3, 6.1 |
| 13.5 | [Frontend packaging & preview container](story13.5_frontend_preview.md) | 13.4, 7.3 |

## Status (2026-10-27)

13.1–13.5 done. Verified in Docker with the fake engine: `static-landing` → a static site with its five routes,
themed, all seven checks passed (one repair), served by its preview; `project-tracker-dynamic` + `two-entity` →
backend and frontend lanes completed, frontend tests passed on mocks, both previews running. `shop-dynamic` has no
golden frontend, so it needs a real engine to verify (not run: paid engines are only used when asked).

## Epic acceptance

- `examples/frontend-specs/static-landing.json` → a static site whose page count and routes equal the spec,
  themed with the spec's colours, served by its preview container.
- `examples/frontend-specs/shop-dynamic.json` → a dynamic app that builds, passes its tests on mocks
  (`MOCK_TEST_API=true`), and uses only contract operations.
